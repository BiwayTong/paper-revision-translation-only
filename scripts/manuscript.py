"""List, select and replace prose in a UTF-8 text file or Word manuscript."""
import argparse
import copy
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from zipfile import ZipFile

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
DOC = "word/document.xml"
SPACE = "{http://www.w3.org/XML/1998/namespace}space"


@dataclass
class Piece:
    text: str
    nodes: tuple = ()


@dataclass
class Block:
    style: str
    context: str
    pieces: list
    line: int = -1
    protected: bool = False


def check(condition, message):
    if not condition:
        raise ValueError(message)


def word_blocks(root):
    from lxml import etree as ET
    fields = set()
    depth = 0
    for n in root.iter():
        if n.tag == W+"fldChar":
            kind = n.get(W+"fldCharType")
            depth += int(kind == "begin") - int(kind == "end")
        if depth and n.tag == W+"t":
            fields.add(n)
    body = root.find(W+"body")
    for p in body.iter(W+"p"):
        # Text boxes and nested paragraphs are not part of their anchor paragraph.
        if any(n.tag == W+"p" for n in p.iterancestors()):
            continue
        visible = [n for n in p.iter(W+"t") if next(n.iterancestors(W+"p")) is p]
        context = "".join(n.text or "" for n in visible)
        if not context.strip():
            continue
        ps = p.find(W+"pPr/"+W+"pStyle")
        style = ps.get(W+"val", "") if ps is not None else "Normal"
        if any(n.tag == W+"tc" for n in p.iterancestors()):
            style += " (table)"
        pieces, assigned = [], set()
        previous = None
        group = []
        def flush():
            if group:
                pieces.append(Piece("".join(n.text or "" for n in group), tuple(group)))
                group.clear()
        # Revisions and content controls require their own layout-aware editing.
        locked = any(n.tag in (W+"ins", W+"del", W+"sdt", W+"moveFrom", W+"moveTo")
                     for n in list(p.iterancestors()) + list(p.iter()))
        for run in p:
            if locked or run.tag != W+"r":
                flush()
                previous = None
                continue
            props = run.find(W+"rPr")
            key = ET.tostring(props, method="c14n") if props is not None else b""
            if key != previous:
                flush()
            previous = key
            for child in run:
                if child.tag == W+"t" and child not in fields:
                    group.append(child)
                    assigned.add(child)
                elif child.tag != W+"rPr":
                    flush()
        flush()
        yield Block(style, context, pieces, protected=any(n not in assigned for n in visible))


class Manuscript:
    def __init__(self, path):
        self.path = path
        self.changed = False
        self.kind = path.suffix.lower()
        self.fingerprint = hashlib.sha256(path.read_bytes()).hexdigest()
        if self.kind == ".docx":
            from lxml import etree as ET
            with ZipFile(path) as archive:
                self.root = ET.fromstring(archive.read(DOC))
            self.blocks = list(word_blocks(self.root))
        elif self.kind == ".txt":
            raw = path.read_bytes()
            self.encoding = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
            self.lines = raw.decode(self.encoding).splitlines(keepends=True)
            self.blocks = [Block("text", line.rstrip("\r\n"), [Piece(line.rstrip("\r\n"))], i)
                           for i, line in enumerate(self.lines) if line.strip()]
        else:
            raise ValueError("Use .docx or UTF-8 .txt; first save pasted prose as a local .txt")

    def manifest(self, selection):
        spans = {}
        for index in selection:
            b = self.blocks[index]
            for j, piece in enumerate(b.pieces):
                text = piece.text.strip()
                if text and any(c.isalpha() for c in text):
                    spans[f"P{len(spans)+1:03d}"] = dict(block=index, piece=j, text=text)
        check(spans, "The selection contains no editable prose; inspect protected formatting")
        return dict(sha256=self.fingerprint, blocks=selection, spans=spans)

    def replace(self, span, edited):
        block = self.blocks[span["block"]]
        piece = block.pieces[span["piece"]]
        original = piece.text
        check(original.strip() == span["text"], "Source text differs")
        if edited == span["text"]:
            return
        self.changed = True
        start = len(original) - len(original.lstrip())
        end = len(original.rstrip())
        new = original[:start] + edited + original[end:]
        if self.kind == ".txt":
            line = self.lines[block.line]
            self.lines[block.line] = new + line[len(original):]
        else:
            first, *rest = piece.nodes
            first.text = new
            if new != new.strip():
                first.set(SPACE, "preserve")
            for n in rest:
                n.text = ""

    def write(self, path):
        check(path.suffix.lower() == self.kind, "Choose the same extension as the source")
        with tempfile.TemporaryDirectory(dir=path.parent) as folder:
            staged = Path(folder)/"verified"
            if not self.changed:
                shutil.copyfile(self.path, staged)
                check(hashlib.sha256(staged.read_bytes()).hexdigest() == self.fingerprint, "The source file has changed")
                if self.kind == ".docx":
                    with ZipFile(staged) as out:
                        check(out.testzip() is None, "Invalid output archive")
            elif self.kind == ".txt":
                staged.write_bytes("".join(self.lines).encode(self.encoding))
            else:
                from lxml import etree as ET
                payload = ET.tostring(self.root, encoding="UTF-8", xml_declaration=True, standalone=True)
                with ZipFile(self.path) as src:
                    with ZipFile(staged, "w") as out:
                        for entry in src.infolist():
                            out.writestr(copy.copy(entry), payload if entry.filename == DOC else src.read(entry))
                    with ZipFile(staged) as out:
                        check(out.testzip() is None and src.namelist() == out.namelist(), "Invalid output archive")
                        for name in src.namelist():
                            check(out.read(name) == (payload if name == DOC else src.read(name)), f"Unexpected change: {name}")
            os.link(staged, path)  # Existing manuscripts and completed outputs are never overwritten.


def selected(spec, size):
    if spec == "all":
        return list(range(size))
    indices = set()
    for item in spec.split(","):
        match = re.fullmatch(r"B(\d+)(?:-B(\d+))?", item.strip())
        check(match, f"Invalid block selector: {item}")
        a = int(match[1])
        b = int(match[2] or match[1])
        check(1 <= a <= b <= size, f"Block outside manuscript: {item}")
        indices.update(range(a-1, b))
    return sorted(indices)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    cmds = parser.add_subparsers(dest="command", required=True)
    for name in ("list", "prepare", "merge"):
        cmd = cmds.add_parser(name)
        cmd.add_argument("source", type=Path)
        if name == "prepare":
            cmd.add_argument("job", type=Path)
            cmd.add_argument("--blocks", required=True, help="B002,B004-B007 or all")
        if name == "merge":
            cmd.add_argument("job", type=Path)
            cmd.add_argument("output", type=Path)
    args = parser.parse_args()
    doc = Manuscript(args.source)
    if args.command == "list":
        for i, block in enumerate(doc.blocks, 1):
            flag = " [protected text]" if block.protected else ""
            print(f"B{i:03d}\t{block.style}{flag}\t{block.context}")
    elif args.command == "prepare":
        scope = doc.manifest(selected(args.blocks, len(doc.blocks)))
        originals = {k: v["text"] for k, v in scope["spans"].items()}
        with tempfile.TemporaryDirectory(dir=args.job.parent) as tmp:
            staging = Path(tmp)/"job"
            staging.mkdir()
            for name, value in (("scope", scope), ("original", originals)):
                (staging/(name+".json")).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
            check(not args.job.exists(), "Choose a new job folder")
            staging.rename(args.job)
        print(f"Prepared {len(originals)} editable units")
        for i in scope["blocks"]:
            if doc.blocks[i].protected:
                print(f"B{i+1:03d}: protected text retained; review this block against the requested scope")
    else:
        scope = json.loads((args.job/"scope.json").read_text(encoding="utf-8"))
        check(doc.fingerprint == scope["sha256"], "The source file has changed")
        indices = scope["blocks"]
        check(indices == sorted(set(indices)) and all(0 <= i < len(doc.blocks) for i in indices), "Invalid scope")
        check(doc.manifest(indices) == scope, "The saved selection no longer matches the manuscript")
        edits = json.loads((args.job/"final.json").read_text(encoding="utf-8"))
        check(isinstance(edits, dict) and edits.keys() == scope["spans"].keys(), "Final IDs differ from the original selection")
        for k, span in scope["spans"].items():
            value = edits[k]
            check(isinstance(value, str) and value.strip() and not any(ch in value for ch in "\n\r\t"), f"Invalid text for {k}")
            doc.replace(span, value.strip())
        doc.write(args.output)


if __name__ == "__main__":
    try:
        main()
    except (OSError, KeyError, ValueError) as exc:
        raise SystemExit(str(exc))
