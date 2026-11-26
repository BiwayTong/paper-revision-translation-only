"""Offline regression tests. No user credentials or network access needed."""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import google_rounds as rounds


class TranslationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.job = Path(self.tmp.name)
        self.put("baseline.json", {"P001": "First.", "P002": "Second."})

    def put(self, name, data):
        path = self.job / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def run_leg(self, n=1, target="zh", input_form=None, output_form=None):
        rounds.run(SimpleNamespace(job=self.job, round=n, to=target,
                                   import_web=input_form, export_web=output_form))

    def client(self):
        with patch.dict(os.environ, {"GOOGLE_TRANSLATE_API_KEY": "offline-fixture"}):
            return rounds.GoogleTranslator()

    def test_api_request_and_raw_response(self):
        client = self.client()
        def fake_open(req, timeout):
            self.assertEqual(req.full_url, rounds.ENDPOINT)
            self.assertEqual(req.get_method(), "POST")
            self.assertEqual(req.get_header("X-goog-api-key"), "offline-fixture")
            self.assertEqual(json.loads(req.data), {"q": ["红 & 蓝"], "source": "zh-CN",
                                                     "target": "en", "format": "text"})
            return io.BytesIO(b'{"data":{"translations":[{"translatedText":" Red &amp; blue. "}]}}')
        with patch.object(client.opener, "open", side_effect=fake_open):
            self.assertEqual(client.translate("红 & 蓝", "en"), " Red &amp; blue. ")

    def test_google_error_does_not_complete_or_expose_response(self):
        client = self.client()
        error = {"error": {"message": "PRIVATE_SAMPLE", "details": [{"reason": "SERVICE_DISABLED"}]}}
        refused = HTTPError(rounds.ENDPOINT, 403, "Denied", {}, io.BytesIO(json.dumps(error).encode()))
        with patch.object(rounds, "GoogleTranslator", return_value=client), patch.object(client.opener, "open", side_effect=refused):
            with self.assertRaisesRegex(ValueError, "403 SERVICE_DISABLED") as failure:
                self.run_leg()
        self.assertNotIn("PRIVATE_SAMPLE", str(failure.exception))
        self.assertFalse((self.job / "r1-zh-raw.json").exists())
        self.assertEqual(list((self.job / ".records").rglob("*.json")), [])

    def test_partial_restart_with_source_and_direction_validation(self):
        path = self.job / "form.json"
        self.run_leg(output_form=path)
        form = json.loads(path.read_text())
        form["paragraphs"]["P001"]["translation"] = "一"
        self.put(path.name, form)
        with self.assertRaisesRegex(ValueError, "P002"):
            self.run_leg(input_form=path)
        client = self.client()
        with patch.object(rounds, "GoogleTranslator", return_value=client), patch.object(client, "translate", return_value="二") as translate:
            self.run_leg()
            self.run_leg()
            translate.assert_called_once_with("Second.", "zh")
        records = self.job / ".records" / "r1-zh"
        self.assertEqual(json.loads((records / "P001.json").read_text())["provider"], rounds.WEB_PROVIDER)
        path2 = records / "P002.json"
        api_record = json.loads(path2.read_text())
        self.assertEqual(api_record["provider"], rounds.API_PROVIDER)
        for changes in ({"target_language":"en"}, {"provider":"another-provider"}):
            path2.write_text(json.dumps(dict(api_record, **changes)))
            with self.assertRaisesRegex(ValueError,"no longer matches"):
                self.run_leg()
        path2.write_text(json.dumps(api_record))
        form["round"] = 2
        self.put(path.name, form)
        with self.assertRaisesRegex(ValueError, "different round"):
            self.run_leg(input_form=path)
        form["round"] = 1
        form["paragraphs"]["P001"]["source"] = "Wrong."
        self.put(path.name, form)
        with self.assertRaisesRegex(ValueError, "source differs"):
            self.run_leg(input_form=path)


if __name__ == "__main__":
    unittest.main()
