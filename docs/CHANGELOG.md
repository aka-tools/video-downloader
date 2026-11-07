# Video Downloader — Changelog

**Versioning rule (set by the owner):** everything stays **V1** until the owner says otherwise.
Users see "V1". Internally the app uses the number 1.0.0 (for the update check).

---

## V1 — November 2026 (current)

**Lectures (Canvas / Panopto)**
- Sign in to Canvas once inside the app; afterwards paste a Canvas lecture page link and click
  Download. The app finds the Panopto video by itself.
- Transcript saved as timestamped bullet points (`<title> - transcript.txt`).
- Subtitles built into the .mp4 AND saved as "<video name>.srt" next to it, so CC works in
  Windows Media Player, Films & TV and VLC (Media Player doesn't read subtitles inside .mp4).
- YouTube captions converted to .srt; clear log message when a video has no captions.

**Other videos**
- YouTube, Vimeo and 1,000+ sites; quality options incl. audio-only MP3; several links, playlists.
- Captions: exactly original language + English + Arabic, 3 s pause between requests.
- Captions never cost you the video: if the site refuses them (e.g. YouTube HTTP 429),
  the app retries with the original track only, then saves the video without captions.

**App**
- Professional window: icon, menus (File / Account / Help), sign-in status, remembered settings.
- Safe update check (Help → Check for updates; off until a GitHub repository is set).
- Copyright "© 2026 AKA. All rights reserved." in the app, installer, .exe details and license.
- Freeware license (LICENSE.txt): free to use and share unmodified; no selling or modifying.

**Installation**
- ONE file: `VideoDownloader-Setup-V1.exe`. It unpacks everything during installation,
  adds Start-menu/Desktop shortcuts, and appears in Settings → Apps with an uninstaller.
- No administrator rights needed. Uninstall also removes the saved login, settings and logs.
- `Setup.bat` (owner only) builds the installer and installs it in one click.
- Tidy folder: only `Setup.bat` in the main folder; everything else in `app\`, `build_tools\`, `docs\`;
  temporary build files go to a hidden `_build\` folder that is removed afterwards.

**Security (pre-launch audit, see SECURITY_AUDIT.md)**
- Saved login encrypted with Windows DPAPI; login cookies kept in memory only, limited to
  Canvas + Panopto.
- https-only links; automation restricted to the configured Canvas site + Panopto.
- Hidden sign-in browser locked down (no permissions, no downloads, invalid certificates refused).
- Exact, hash-verified dependencies from the official package index; fresh isolated build.
- Access tokens redacted from logs; free-disk-space check; no telemetry.
- GitHub-ready: one-click release (Actions → "Build & release"), automatic checks on every change,
  16 automated tests (incl. the owner's rules: label stays V1, publisher "AKA" only),
  update check stamped with the official repository, private vulnerability reporting.

---

## Ideas for later (when the owner decides on a new version)
- Download a whole Canvas module/course in one go
- Cancel / pause button and a download queue
- AI summary of the transcript (key points + timestamps)
- Signed installer (removes the Windows SmartScreen warning)
