"""Run one Apple Translate leg of a three-round revision. Edits are supplied separately."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_texts(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data or any(not re.fullmatch(r"P[0-9]+", k) or
            not isinstance(v, str) or not v.strip() for k, v in data.items()):
        raise ValueError(f"Invalid ID-to-text file: {path}")
    return data


def publish(path, data):
    # A completed record is immutable, even if two invocations overlap.
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    with tempfile.TemporaryDirectory(dir=path.parent) as folder:
        staged = Path(folder)/"new"
        staged.write_text(payload, encoding="utf-8")
        try:
            os.link(staged, path)
        except FileExistsError:
            if json.loads(path.read_text(encoding="utf-8")) != data:
                raise ValueError(f"Conflicting record at {path}; use a new job folder for revised inputs") from None


def translate(text, shortcut):
    with tempfile.TemporaryDirectory() as tmp:
        inp, out = Path(tmp)/"input.txt", Path(tmp)/"output.txt"
        inp.write_bytes(text.encode("utf-8"))
        subprocess.run(["/usr/bin/shortcuts", "run", shortcut, "--input-path", str(inp),
                        "--output-path", str(out), "--output-type", "public.plain-text"],
                       check=True, capture_output=True, timeout=180)
        raw = out.read_bytes().decode("utf-8")
        if not raw.strip() or raw.strip() == text.strip():
            raise ValueError("Empty or unchanged output; verify the translation action before accepting this item")
        return raw


def run(args):
    job = args.job
    base = read_texts(job / "baseline.json")
    ids = set(base)
    for n in range(1, args.round + 1):
        for direction in ("zh", "en"):
            is_target = (n, direction) == (args.round, args.to)
            if direction == "zh":
                source = base if n == 1 else read_texts(job / f"r{n-1}-en-edit.json")
            else:
                source = read_texts(job / f"r{n}-zh-edit.json")
            if set(source) != ids:
                raise ValueError("Edited IDs do not match the baseline")
            tag = f"r{n}-{direction}"
            records = job / ".records" / tag
            if is_target:
                records.mkdir(parents=True, exist_ok=True)
            raw = {}
            for key, value in source.items():
                path = records / f"{key}.json"
                if not path.exists() and is_target:
                    print(f"{tag} {key}", flush=True)
                    result = translate(value, args.shortcut)
                    publish(path, dict(input_sha256=digest(value), output=result,
                                       output_sha256=digest(result), shortcut=args.shortcut))
                rec = json.loads(path.read_text(encoding="utf-8"))
                if rec["input_sha256"] != digest(value) or rec["output_sha256"] != digest(rec["output"]):
                    raise ValueError(f"{tag}/{key} no longer matches its input or output")
                raw[key] = rec["output"]
            raw_file = job / f"{tag}-raw.json"
            if is_target:
                publish(raw_file, raw)
                return
            if read_texts(raw_file) != raw:
                raise ValueError(f"Earlier raw outputs have changed: {raw_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path)
    parser.add_argument("round", type=int, choices=(1, 2, 3))
    parser.add_argument("to", choices=("zh", "en"))
    parser.add_argument("shortcut", help="name of the configured Apple Translate shortcut")
    try:
        run(parser.parse_args())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as err:
        parser.exit(1, f"{err}\n")
