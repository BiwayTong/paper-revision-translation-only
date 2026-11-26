"""Run one English/Chinese translation leg using Google Cloud Translation Basic v2."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.error
import urllib.request

ENDPOINT = "https://translation.googleapis.com/language/translate/v2"
LANGUAGES = {"zh": ("en", "zh-CN"), "en": ("zh-CN", "en")}
API_PROVIDER = "google-cloud-translation-v2"
WEB_PROVIDER = "google-translate-web"


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_texts(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data or any(not re.fullmatch(r"P[0-9]+", k) or
            not isinstance(v, str) or not v.strip() for k, v in data.items()):
        raise ValueError(f"Invalid ID-to-text file: {path}")
    return data


def read_spans(job):
    scope = json.loads((job / "scope.json").read_text(encoding="utf-8"))
    spans = scope.get("spans") if isinstance(scope, dict) else None
    if not isinstance(spans, list) or not spans:
        raise ValueError("Expected numbered highlights in scope.json")
    found = set()
    for span in spans:
        if not isinstance(span, dict):
            raise ValueError("Invalid highlight in scope.json")
        key = span.get("id")
        value = span.get("text")
        if not isinstance(key, str) or not re.fullmatch(r"P[0-9]+", key) or key in found:
            raise ValueError("Invalid or duplicate highlight ID in scope.json")
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Missing source text for {key}")
        pages = span.get("pages", [])
        if not isinstance(pages, list) or any(type(p) is not int or p < 1 for p in pages):
            raise ValueError(f"Invalid PDF page numbers for {key}")
        found.add(key)
    return spans


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


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GoogleTranslator:
    def __init__(self):
        self.opener = urllib.request.build_opener(NoRedirect())
        self.key = os.environ.get("GOOGLE_TRANSLATE_API_KEY")
        if not self.key:
            try:
                import google.auth
                from google.auth.transport.requests import Request
            except ImportError:
                raise ValueError("Set GOOGLE_TRANSLATE_API_KEY or install google-auth[requests] for ADC.") from None
            from google.auth.exceptions import GoogleAuthError
            try:
                self.credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
                self.transport = Request()
            except GoogleAuthError:
                raise ValueError("Google credentials unavailable. Configure ADC or GOOGLE_TRANSLATE_API_KEY.") from None

    def translate(self, text, direction):
        src, dst = LANGUAGES[direction]
        body = json.dumps(dict(q=[text], source=src, target=dst, format="text"), ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if self.key:
            headers["X-Goog-Api-Key"] = self.key
        else:
            from google.auth.exceptions import GoogleAuthError
            try:
                self.credentials.before_request(self.transport, "POST", ENDPOINT, headers)
            except GoogleAuthError:
                raise ValueError("Google authentication failed. Check or renew the configured ADC credentials.") from None
        req = urllib.request.Request(ENDPOINT, data=body, headers=headers, method="POST")
        try:
            with self.opener.open(req, timeout=90) as response:
                data = json.load(response)
        except urllib.error.HTTPError as exc:
            # Display only Google's status and reason codes. Error bodies may contain customer data.
            try:
                error = json.load(exc)["error"]
                codes = [item.get("reason", "") for item in error.get("details", []) + error.get("errors", [])]
                reason = ", ".join(c for c in codes if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", c))
            except (ValueError, KeyError, TypeError, AttributeError):
                reason = ""
            raise ValueError(f"Google Translation HTTP {exc.code} {reason}. This item was not recorded.") from None
        try:
            result, = data["data"]["translations"]
            raw = result["translatedText"]
        except (KeyError, TypeError, ValueError):
            raise ValueError("Google returned an unexpected translation response.") from None
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("Google returned an empty translation.")
        return raw


def verify_record(rec, source, direction):
    src, dst = LANGUAGES[direction]
    return (isinstance(rec, dict) and rec.get("provider") in (API_PROVIDER, WEB_PROVIDER)
            and (rec.get("source_language"), rec.get("target_language")) == (src, dst)
            and rec.get("input_sha256") == digest(source)
            and isinstance(rec.get("output"), str) and bool(rec["output"].strip())
            and rec.get("output_sha256") == digest(rec["output"]))


def web_form(round_number, direction, source):
    src, dst = LANGUAGES[direction]
    return {"round": round_number, "source_language": src, "target_language": dst,
            "paragraphs": {key: {"source": value, "translation": ""} for key, value in source.items()}}


def read_web_results(path, expected):
    form = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(form, dict) or any(form.get(k) != expected[k] for k in ("round", "source_language", "target_language")):
        raise ValueError("The web form belongs to a different round or language pair.")
    rows = form.get("paragraphs")
    if not isinstance(rows, dict) or not rows or not rows.keys() <= expected["paragraphs"].keys():
        raise ValueError("The web form has missing or unknown paragraph IDs.")
    results = {}
    for key, row in rows.items():
        if not isinstance(row, dict) or row.get("source") != expected["paragraphs"][key]["source"]:
            raise ValueError(f"The web source differs for {key}. Export the current inputs.")
        value = row.get("translation")
        if not isinstance(value, str):
            raise ValueError(f"Expected a translation string for {key}.")
        if value.strip():
            results[key] = value
    return results


def run(args):
    job = args.job
    base = read_texts(job / "baseline.json")
    ids = set(base)
    original = {span["id"]: span["text"] for span in read_spans(job)}
    if ids != original.keys():
        raise ValueError("Baseline IDs do not match the selected highlights in scope.json")
    publish(job / "original.json", original)
    manual = {}
    client = None
    for n in range(1, args.round + 1):
        for direction in ("zh", "en"):
            is_target = (n, direction) == (args.round, args.to)
            if direction == "zh":
                source = base if n == 1 else read_texts(job / f"r{n-1}-en-edit.json")
            else:
                source = read_texts(job / f"r{n}-zh-edit.json")
            if set(source) != ids:
                raise ValueError("Edited IDs do not match the baseline")
            if is_target and (args.export_web or args.import_web):
                form = web_form(n, direction, source)
                if args.export_web:
                    publish(args.export_web, form)
                    return
                manual = read_web_results(args.import_web, form)
            tag = f"r{n}-{direction}"
            records = job / ".records" / tag
            if is_target:
                records.mkdir(parents=True, exist_ok=True)
            raw = {}
            for key, value in source.items():
                path = records / f"{key}.json"
                if not path.exists() and is_target:
                    print(f"{tag} {key}", flush=True)
                    if args.import_web and key not in manual:
                        continue
                    if args.import_web:
                        result = manual[key]
                    else:
                        if client is None:
                            client = GoogleTranslator()
                        result = client.translate(value, direction)
                    src, dst = LANGUAGES[direction]
                    publish(path, dict(input_sha256=digest(value), output=result,
                                       output_sha256=digest(result),
                                       provider=WEB_PROVIDER if args.import_web else API_PROVIDER,
                                       source_language=src, target_language=dst))
                rec = json.loads(path.read_text(encoding="utf-8"))
                if not verify_record(rec, value, direction):
                    raise ValueError(f"{tag}/{key} no longer matches its input or output")
                if is_target and key in manual and manual[key] != rec["output"]:
                    raise ValueError(f"Conflicting Google output at {tag}/{key}")
                raw[key] = rec["output"]
            raw_file = job / f"{tag}-raw.json"
            if is_target:
                if raw.keys() != ids:
                    raise ValueError("Saved partial translations; still needed: " + ", ".join(sorted(ids - raw.keys())))
                publish(raw_file, raw)
                return
            if read_texts(raw_file) != raw:
                raise ValueError(f"Earlier raw outputs have changed: {raw_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path)
    parser.add_argument("round", type=int, choices=(1, 2, 3))
    parser.add_argument("to", choices=("zh", "en"))
    web = parser.add_mutually_exclusive_group()
    web.add_argument("--export-web", type=Path, help="Save the current numbered inputs in a new Google Translate web form")
    web.add_argument("--import-web", type=Path, help="Import a form filled with raw outputs actually obtained from Google Translate on the web")
    try:
        args = parser.parse_args()
        run(args)
    except (OSError, ValueError, KeyError) as err:
        parser.exit(1, f"{err}\n")
