# Video Downloader — project overview

**Current version:** V1 (internal 1.0.0) · **Publisher / copyright:** AKA (owner prefers his full name not to appear anywhere in the product) (freeware EULA, LICENSE.txt) · **Platform:** Windows 10/11 x64

## How to work with the owner (from his Obsidian vault: CLAUDE.md, 00 Brain/User, Soul, Identity)
- Mode: **AI Instructor & Engineer** - teach while building; explain the why, not just the how.
- Bullets, short by default; full reasoning only on request. Dry, direct tone.
- No hedging words. Uncertain → say so plainly + what is needed to decide.
- Push back when he is wrong. Flag gaps proactively. Cite the source file.
- Single source of truth: one trusted place per thing.

## What it is
Desktop app that downloads Canvas/Panopto lecture recordings (Zigurat) and videos from
YouTube, Vimeo and 1,000+ sites, with subtitles embedded in the .mp4 and a transcript
as timestamped bullet points (`<title> - transcript.txt`).

## Master copy
**GitHub repository (public) = single source of truth** once published (see docs/PUBLISHING.md).
This Claude project mirrors it. Releases: Actions → "Build & release" → Run workflow.

## Folder layout (main folder shows only Setup.bat)
```
VideoDownloader-V1\
├─ Setup.bat                 ← the only file in front: builds + installs, outputs VideoDownloader-Setup-V1.exe here
├─ app\                      program source
│   video_downloader.py · canvas_helper.py · secure_store.py · transcript.py · updater.py · icon.ico · LICENSE.txt
├─ build_tools\              build scripts
│   VideoDownloader.iss (installer) · make_version_info.py · requirements.lock · Start.bat (dev mode)
├─ docs\                     README · CHANGELOG · SECURITY · SECURITY_AUDIT · THIRD_PARTY_NOTICES · PROJECT · PUBLISHING
├─ build_tools\tests\        automated tests (run by GitHub on every change)
├─ .github\                  GitHub front page (README.md) + workflows (check.yml, release.yml)
├─ .gitignore                 keeps build output and secrets out of the repo
└─ _build\  (hidden, temporary - created during a build and deleted afterwards)
```
In this Claude project the same files are stored under `src/app/`, `src/build_tools/`, `src/docs/`.

`icon.ico` is binary and not stored here. Keep it from the master ZIP
(`VideoDownloader-V1.zip`), or regenerate it: a blue rounded square with a white
play triangle and a download arrow.

## Key decisions
- **Everything stays V1 until the owner explicitly says otherwise.** Do not bump the version or rename files with new numbers. (Internal number 1.0.0, label `APP_LABEL = "V1"`.)
- Distribute ONE file only: `VideoDownloader-Setup-V1.exe` (no ZIP, no .bat, no links).
- Copyright/publisher shown as "AKA" only - never the owner's full name. All rights reserved; free to use and share unmodified.
- The installer is ONE self-extracting .exe: everything is packed inside and unpacked during installation (no web download during install).
- Professional look.
- Security first: DPAPI-encrypted login, cookies in memory only, https-only,
  hash-locked dependencies, checksummed + attested releases, no telemetry.
- Subtitles: embedded in the .mp4 AND a same-name `<video>.srt` next to it (Windows Media Player only shows CC from a matching .srt file). Transcript = bullets + timestamps.
- YouTube etc.: only the original caption track + English + Arabic.

## Open items / next steps
1. Publish the GitHub repo (docs/PUBLISHING.md). `UPDATE_REPO` is stamped automatically by the release build.
2. Code signing (removes the SmartScreen warning) before any public launch.
3. Enable GitHub private vulnerability reporting (no email published).
4. Check that Zigurat and Panopto terms allow public distribution.
5. Final smoke test on a clean Windows PC.

## Ideas backlog
Whole Canvas module/course download · cancel/pause + queue · AI summary of the transcript.
