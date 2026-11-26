"""Verify the three translation rounds and export a readable revision archive."""
import argparse
import json
import os
from pathlib import Path
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED
from google_rounds import read_texts, verify_record


def export(job, destination):
    original = read_texts(job / "original.json")
    def draft(name):
        values = read_texts(job / (name + ".json"))
        if values.keys() != original.keys():
            raise ValueError(f"IDs changed in {name}")
        return values
    baseline = draft("baseline")
    current = baseline
    with tempfile.TemporaryDirectory(dir=destination.parent) as tmp:
        out = Path(tmp)/"process.zip"
        with ZipFile(out, "w", ZIP_DEFLATED) as archive:
            for name in ("scope.json", "original.json", "baseline.json", "review.md"):
                archive.write(job/name, name)
            for n in (1, 2, 3):
                sections = []
                for direction, raw_title, edit_title in (
                        ("zh", "Google 翻译中文原文", "中文调整稿"),
                        ("en", "Google 翻译英文回译原文", "本轮英文稿")):
                    tag = f"r{n}-{direction}"
                    raw = draft(tag+"-raw")
                    for ident in original:
                        rec_file = job/".records"/tag/(ident+".json")
                        rec = json.loads(rec_file.read_text(encoding="utf-8"))
                        if not verify_record(rec, current[ident], direction) or rec["output"] != raw[ident]:
                            raise ValueError(f"Translation record differs: {tag}/{ident}")
                        archive.write(rec_file, f"records/{tag}/{ident}.json")
                    current = draft(tag+"-edit")
                    for suffix in ("raw", "edit"):
                        filename = f"{tag}-{suffix}.json"
                        archive.write(job/filename, filename)
                    sections.extend([(raw_title, raw), (edit_title, current)])
                lines = [f"# 第 {n} 轮"]
                for ident in original:
                    lines.append("## "+ident)
                    for title, values in sections:
                        lines.extend(["### "+title, values[ident]])
                archive.writestr(f"round-{n}.md", "\n\n".join(lines)+"\n")
            draft("check")
            final = draft("final")
            for name in ("check.json", "final.json"):
                archive.write(job/name, name)
            final_zh = draft("r3-zh-edit")
            lines = ["# 段落对照"]
            for ident in original:
                lines.extend(["## "+ident,"### 英文基准稿",baseline[ident],"### 第三轮中文调整稿",
                              final_zh[ident],"### 最终英文稿",final[ident]])
            archive.writestr("comparison.md","\n\n".join(lines)+"\n")
        with ZipFile(out) as archive:
            if archive.testzip():
                raise ValueError("Invalid process ZIP")
        os.link(out,destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        export(args.job,args.output)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1,f"{exc}\n")
