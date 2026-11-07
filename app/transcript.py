# Copyright (c) 2026 AKA. All rights reserved.
# Part of Video Downloader - see LICENSE.txt. Unauthorised copying or modification is prohibited.
"""Turn .srt / .vtt subtitle files into a readable, timestamped bullet-point transcript."""
import re

_TS = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})\s*-->")
_TAG = re.compile(r"<[^>]+>|\{\\[^}]*\}")
_SENTENCE_END = (".", "?", "!", "…")


def _parse(path):
    cues, start, buf = [], None, []

    def flush():
        if start is not None and buf:
            text = " ".join(buf).strip()
            if text:
                cues.append((start, text))
        buf.clear()

    with open(path, encoding="utf-8-sig", errors="ignore") as f:
        for raw in f:
            s = raw.strip()
            m = _TS.match(s)
            if m:
                flush()
                h, mi, se = int(m.group(1) or 0), int(m.group(2)), int(m.group(3))
                start = h * 3600 + mi * 60 + se
                continue
            if not s:
                flush()
                continue
            if s.startswith(("WEBVTT", "Kind:", "Language:", "NOTE", "STYLE", "REGION")):
                continue
            if s.isdigit() and not buf:
                continue  # SRT cue number
            s = _TAG.sub("", s).strip()
            if s:
                buf.append(s)
    flush()

    # drop rolling duplicates (common in auto-captions)
    out, last = [], ""
    for t, text in cues:
        if text == last or (last and text.startswith(last) and len(text) - len(last) < 3):
            continue
        if last and text.startswith(last):
            text = text[len(last):].strip()
        out.append((t, text))
        last = text
    return out


def _fmt(sec):
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def to_bullets(path, title="", min_gap=30, max_gap=75):
    """
    Group caption lines into bullets of roughly 30-75 seconds, broken at sentence ends.
    Returns the transcript text.
    """
    cues = _parse(path)
    bullets, cur_t, cur = [], None, []
    for t, text in cues:
        if cur_t is not None and t - cur_t >= max_gap:  # long pause / jump: start a new bullet
            bullets.append((cur_t, " ".join(cur)))
            cur_t, cur = None, []
        if cur_t is None:
            cur_t = t
        cur.append(text)
        joined = " ".join(cur)
        span = t - cur_t
        if (span >= min_gap and joined.rstrip().endswith(_SENTENCE_END)) or span >= max_gap:
            bullets.append((cur_t, joined))
            cur_t, cur = None, []
    if cur:
        bullets.append((cur_t, " ".join(cur)))

    lines = []
    if title:
        lines += [title, "=" * min(len(title), 80), ""]
    for t, txt in bullets:
        clean = re.sub(r"\s+", " ", txt).strip()
        lines.append(f"• [{_fmt(t)}]  {clean}")
    return "\n".join(lines) + "\n"
