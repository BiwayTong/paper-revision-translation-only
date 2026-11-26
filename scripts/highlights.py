"""Map coloured PDF rectangles to Word character ranges and merge reviewed replacements."""
import argparse
import copy
import hashlib
import json
import os
import shutil
import tempfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile

from lxml import etree as ET

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
PART = "word/document.xml"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normal(text):
    return "".join(c for c in unicodedata.normalize("NFKC", text) if not c.isspace())


def paragraphs(root):
    return root.xpath("./w:body/w:p", namespaces=NS)


def text_nodes(paragraph):
    return paragraph.xpath(".//w:t", namespaces=NS)


def inspect(args):
    import pdfplumber
    with pdfplumber.open(args.pdf) as pdf:
        for p in pdf.pages:
            colors = Counter(str(r["non_stroking_color"]) for r in p.rects if r["fill"])
            print(f"p{p.page_number} {p.width:.1f} × {p.height:.1f}, rects {dict(colors)}, annotations {len(p.annots)}")


def extract(args):
    import pdfplumber
    with ZipFile(args.word) as doc:
        root = ET.fromstring(doc.read(PART))
    texts = ["".join(t.text or "" for t in text_nodes(p)) for p in paragraphs(root)]
    chars, offsets = [], []
    for pi, text in enumerate(texts):
        for index, c in enumerate(text):
            for letter in normal(c):
                chars.append(letter)
                offsets.append((pi, index))
    full = "".join(chars)
    pos = 0
    selected = defaultdict(set)
    with pdfplumber.open(args.pdf) as pdf:
        first, last = args.pages
        require(1 <= first <= last <= len(pdf.pages), "Invalid PDF page range")
        top, bottom = args.y
        for page in pdf.pages[first - 1:last]:
            require(0 <= top < bottom <= page.height, "Invalid body crop for this PDF page")
            body = page.crop((0, top, page.width, bottom))
            rects = [r for r in body.rects if r["fill"] and isinstance(r["non_stroking_color"], (tuple, list))
                     and len(r["non_stroking_color"]) == 3
                     and max(abs(a-b) for a, b in zip(r["non_stroking_color"], args.rgb)) <= .002]
            used = set()
            for line in body.extract_text_lines(return_chars=True):
                for glyph in line["chars"]:
                    token = normal(glyph["text"])
                    if not token:
                        continue
                    require(full.startswith(token, pos), f"PDF/Word text differs on page {page.page_number} near {line['text'][:65]!r}")
                    x = (glyph["x0"] + glyph["x1"]) / 2
                    y = (glyph["top"] + glyph["bottom"]) / 2
                    for n, rect in enumerate(rects):
                        if rect["x0"] <= x <= rect["x1"] and rect["top"] <= y <= rect["bottom"]:
                            used.add(n)
                            for address in offsets[pos:pos + len(token)]:
                                selected[address].add(page.page_number)
                    pos += len(token)
            require(len(used) == len(rects), f"Selected colour includes a rectangle without mapped text on page {page.page_number}")
    require(pos == len(full), "The supplied pages do not reproduce the complete Word body")
    require(selected, "No text under the chosen colour; inspect the PDF marking type and layout")
    spans = []
    for (pi, index), pages in sorted(selected.items()):
        prev = spans[-1] if spans else None
        if prev and pi == prev["paragraph"] and not texts[pi][prev["end"]:index].strip():
            prev["end"] = index + 1
            prev["pages"].update(pages)
        else:
            spans.append(dict(id=f"P{len(spans)+1:03d}", paragraph=pi, start=index, end=index+1, pages=set(pages)))
    for h in spans:
        h["text"] = texts[h["paragraph"]][h["start"]:h["end"]]
        h["pages"] = sorted(h["pages"])
    manifest = dict(word_sha256=sha(args.word), pdf_sha256=sha(args.pdf), spans=spans)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"{len(spans)} spans")


def merge(args):
    scope = json.loads(args.scope.read_text(encoding="utf-8"))
    replacements = json.loads(args.edits.read_text(encoding="utf-8"))
    require(sha(args.word) == scope["word_sha256"], "Base Word file changed; locate the matching version")
    spans = scope["spans"]
    ids = [s["id"] for s in spans]
    require(ids and len(set(ids)) == len(ids) and set(ids) == set(replacements), "Replacement IDs differ from scope")
    with ZipFile(args.word) as doc:
        root = ET.fromstring(doc.read(PART))
        ps = paragraphs(root)
        previous = None
        changed = 0
        # Reverse order keeps earlier offsets stable when replacement lengths change.
        for s in sorted(spans, key=lambda h: (h["paragraph"], h["start"]), reverse=True):
            pi, a, b = s["paragraph"], s["start"], s["end"]
            require(0 <= pi < len(ps) and 0 <= a < b, "Invalid span offsets")
            require(previous is None or pi != previous[0] or b <= previous[1], "Overlapping spans")
            previous = (pi, a)
            val = replacements[s["id"]]
            require(isinstance(val, str) and val.strip() and not any(c in val for c in "\r\n\t"), "Expected single-paragraph replacement")
            nodes = text_nodes(ps[pi])
            before = "".join(n.text or "" for n in nodes)
            require(before[a:b] == s["text"] and b <= len(before), f"Original span differs at {s['id']}")
            if val == s["text"]:
                continue
            require(not ps[pi].xpath(".//w:fldChar | .//w:fldSimple | .//w:ins | .//w:del", namespaces=NS),
                    f"{s['id']} intersects a paragraph with fields or tracked changes; use formatting-aware editing")
            cursor = 0
            for node in nodes:
                t = node.text or ""
                if cursor <= a and b <= cursor + len(t):
                    require(not node.xpath("ancestor::w:hyperlink", namespaces=NS), f"{s['id']} is a hyperlink; inspect manually")
                    node.text = t[:a-cursor] + val + t[b-cursor:]
                    break
                cursor += len(t)
            else:
                raise ValueError(f"{s['id']} spans multiple Word text nodes; preserve their formatting with a run-aware edit")
            require("".join(n.text or "" for n in nodes) == before[:a]+val+before[b:], "Unexpected paragraph edit")
            changed += 1
        with tempfile.TemporaryDirectory(dir=args.output.parent) as tmp:
            staged = Path(tmp)/"verified.docx"
            if changed:
                payload = ET.tostring(root, encoding="UTF-8", xml_declaration=True, standalone=True)
                with ZipFile(staged, "w") as out:
                    for entry in doc.infolist():
                        out.writestr(copy.copy(entry), payload if entry.filename == PART else doc.read(entry))
                with ZipFile(staged) as check:
                    require(check.testzip() is None and check.namelist() == doc.namelist(), "Invalid output archive")
                    for name in doc.namelist():
                        require(check.read(name) == (payload if name == PART else doc.read(name)), f"Unexpected change in {name}")
            else:
                shutil.copyfile(args.word, staged)
                require(sha(staged) == scope["word_sha256"], "Base Word file changed")
                with ZipFile(staged) as check:
                    require(check.testzip() is None, "Invalid output archive")
            os.link(staged, args.output)  # publish only after validation; existing files are never overwritten
    print(f"{changed} of {len(spans)} verified spans changed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    show = sub.add_parser("inspect", help="sample rectangle colours and count annotations")
    show.add_argument("pdf", type=Path)
    take = sub.add_parser("extract", help="map rectangular highlights against a complete linear Word body")
    take.add_argument("pdf", type=Path)
    take.add_argument("word", type=Path)
    take.add_argument("output", type=Path, help="new JSON scope file")
    take.add_argument("--pages", type=int, nargs=2, required=True, metavar=("FIRST", "LAST"))
    take.add_argument("--y", type=float, nargs=2, required=True, metavar=("TOP", "BOTTOM"))
    take.add_argument("--rgb", type=float, nargs=3, required=True)
    put = sub.add_parser("merge", help="apply a JSON object of ID to final English text")
    for arg in ("word", "scope", "edits", "output"):
        put.add_argument(arg, type=Path)
    args = parser.parse_args()
    try:
        {"inspect": inspect, "extract": extract, "merge": merge}[args.command](args)
    except (ValueError, OSError) as err:
        parser.exit(1, f"{err}\n")


if __name__ == "__main__":
    main()
