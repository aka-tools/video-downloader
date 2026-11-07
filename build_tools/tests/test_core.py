# Copyright (c) 2026 AKA. All rights reserved.
"""
Automated checks, run by GitHub Actions on every change and before every release.
Run locally:  python -m unittest discover -s build_tools/tests -v
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP = os.path.join(ROOT, "app")
sys.path.insert(0, APP)

import importlib.util  # noqa: E402

HAVE_TK = importlib.util.find_spec("tkinter") is not None

import transcript  # noqa: E402
import updater  # noqa: E402

SRT = ("1\n00:00:01,000 --> 00:00:04,000\n<i>Hello everyone.</i>\n\n"
       "2\n00:00:40,000 --> 00:00:44,000\nWelcome to the lecture.\n")
VTT = "WEBVTT\nKind: captions\n\n01:02.500 --> 01:05.000\nHello there.\n"


def write_tmp(text, suffix):
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    return path


class TranscriptTests(unittest.TestCase):
    def test_srt_to_timestamped_bullets(self):
        out = transcript.to_bullets(write_tmp(SRT, ".srt"), title="Lecture")
        self.assertIn("• [00:00:01]  Hello everyone.", out)
        self.assertNotIn("<i>", out)
        self.assertTrue(out.startswith("Lecture\n"))

    def test_vtt_supported(self):
        self.assertIn("• [00:01:02]  Hello there.", transcript.to_bullets(write_tmp(VTT, ".vtt")))


class UpdaterTests(unittest.TestCase):
    def fake(self, payload):
        class R(io.BytesIO):
            status = 200

            def __enter__(s):
                return s

            def __exit__(s, *a):
                return False
        return mock.patch("urllib.request.urlopen", lambda *a, **k: R(json.dumps(payload).encode()))

    def setUp(self):
        self._repo = updater.UPDATE_REPO
        updater.UPDATE_REPO = "owner/video-downloader"

    def tearDown(self):
        updater.UPDATE_REPO = self._repo

    def test_versions(self):
        self.assertEqual(updater.parse_version("v1.2.3"), (1, 2, 3))
        self.assertIsNone(updater.parse_version("latest"))

    def test_newer_release_found(self):
        with self.fake({"tag_name": "v1.1.0",
                        "html_url": "https://github.com/owner/video-downloader/releases/tag/v1.1.0"}):
            self.assertEqual(updater.check("1.0.0")[0], "1.1.0")

    def test_same_version_ignored(self):
        with self.fake({"tag_name": "v1.0.0"}):
            self.assertIsNone(updater.check("1.0.0"))

    def test_prerelease_ignored(self):
        with self.fake({"tag_name": "v9.0.0", "prerelease": True}):
            self.assertIsNone(updater.check("1.0.0"))

    def test_foreign_link_never_opened(self):
        with self.fake({"tag_name": "v1.1.0", "html_url": "https://evil.example/x.exe"}):
            _, page = updater.check("1.0.0")
        self.assertTrue(page.startswith("https://github.com/owner/video-downloader/releases/"))

    def test_bad_repo_name_disables_check(self):
        updater.UPDATE_REPO = "bad repo; del"
        self.assertFalse(updater.is_configured())


class CanvasHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global canvas_helper
        import canvas_helper  # needs playwright installed

    def test_hosts(self):
        self.assertTrue(canvas_helper.is_panopto_host("e-zigurat.cloud.panopto.eu"))
        self.assertFalse(canvas_helper.is_panopto_host("evilpanopto.eu"))
        self.assertTrue(canvas_helper.valid_host("canvas.e-zigurat.com"))
        self.assertFalse(canvas_helper.valid_host("x;rm -rf"))

    def test_only_canvas_and_panopto_cookies_kept(self):
        cookies = [{"domain": ".panopto.eu", "name": "a"},
                   {"domain": "canvas.e-zigurat.com", "name": "b"},
                   {"domain": ".login.microsoftonline.com", "name": "c"}]
        kept = [c["name"] for c in canvas_helper._scoped(cookies, "canvas.e-zigurat.com")]
        self.assertEqual(kept, ["a", "b"])

    def test_automation_refuses_other_sites(self):
        with self.assertRaises(ValueError):
            canvas_helper.resolve("https://evil.example/page", "canvas.e-zigurat.com", print)


@unittest.skipUnless(sys.platform == "win32", "DPAPI exists only on Windows")
class SecureStoreTests(unittest.TestCase):
    def test_round_trip_and_not_plain_text(self):
        import secure_store
        blob = secure_store.protect(b"secret-cookie")
        self.assertNotIn(b"secret-cookie", blob)
        self.assertEqual(secure_store.unprotect(blob), b"secret-cookie")


@unittest.skipUnless(HAVE_TK, "the app window needs tkinter")
class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global vd
        import video_downloader as vd

    def test_tokens_redacted_from_logs(self):
        self.assertEqual(vd.redact("https://cdn.x/v.m3u8?token=SECRET"), "https://cdn.x/v.m3u8?…")
        self.assertIn("id=690b", vd.redact("https://a.panopto.eu/Viewer.aspx?id=690b&auth=zzz"))

    def test_caption_failure_never_loses_the_video(self):
        import yt_dlp
        calls = []

        class Fake:
            def __init__(self, o):
                self.o, self.cookiejar = o, None

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def extract_info(self, url, download):
                calls.append(bool(self.o.get("writesubtitles")))
                if self.o.get("writesubtitles"):
                    raise yt_dlp.utils.DownloadError("Unable to download video subtitles: HTTP Error 429")
                return {"title": "ok"}

        opts = {"writesubtitles": True, "subtitleslangs": ["en"],
                "postprocessors": [{"key": "FFmpegEmbedSubtitle"}]}
        with mock.patch.object(yt_dlp, "YoutubeDL", Fake), mock.patch.object(vd.time, "sleep"):
            info = vd.App._download(None, "https://youtube.com/watch?v=x", opts, [], lambda t: None)
        self.assertEqual(info, {"title": "ok"})
        self.assertEqual(calls, [True, True, False])  # full, original-only, then video without captions


class OwnerRulesTests(unittest.TestCase):
    """The owner's standing decisions, checked automatically."""

    def read(self, *parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
            return f.read()

    def test_version_label_is_v1(self):
        self.assertIn('APP_LABEL = "V1"', self.read("app", "video_downloader.py"))
        out = subprocess.run([sys.executable, os.path.join(ROOT, "build_tools", "make_version_info.py"),
                              os.path.join(tempfile.mkdtemp(), "vi.txt")],
                             capture_output=True, text=True, check=True).stdout.split()
        self.assertEqual(out[1], "V1")

    def test_publisher_is_aka_and_full_name_never_appears(self):
        banned = ("Abdel" + "aal", "Ahmad " + "Khaled")
        for folder, _, files in os.walk(ROOT):
            if any(p in folder for p in (".git" + os.sep, "_build", "__pycache__")) or folder.endswith(".git"):
                continue
            for name in files:
                if name.endswith((".ico", ".exe", ".pyc")):
                    continue
                with open(os.path.join(folder, name), encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                for b in banned:
                    self.assertNotIn(b, text, f"full name found in {name}")
        self.assertIn('APP_AUTHOR = "AKA"', self.read("app", "video_downloader.py"))


if __name__ == "__main__":
    unittest.main()
