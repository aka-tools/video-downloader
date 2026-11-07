# Video Downloader V1

Download lecture recordings (Canvas / Panopto) and videos from YouTube, Vimeo and 1,000+ sites,
with **subtitles** and a **timestamped transcript**.

**[⬇ Download the latest version](../../../releases/latest)**: one file, `VideoDownloader-Setup-V1.exe`
(or click **Releases** on the right side of this page).
Double-click it and click Install. Windows 10/11, no administrator rights needed.

---

## What you get per video
| File | What it is |
|---|---|
| `<title>.mp4` | The video, with subtitles built in |
| `<title>.srt` | Subtitles with the same name, so **CC** works in Windows Media Player and VLC |
| `<title> - transcript.txt` | The transcript as bullet points with timestamps |

## Using it
1. **Canvas lectures:** click **Sign in to Canvas** once. Then copy a lecture page link, open the app and click **Download**. The app finds the Panopto video by itself.
2. **Other sites:** paste the link and click **Download**.

Full guide: [docs/README.txt](../docs/README.txt)

## Privacy & security
- No telemetry, no accounts, no cloud. The saved Canvas login is encrypted with Windows DPAPI.
- Every release is built by GitHub Actions on a clean machine, scanned, and published with a
  SHA-256 checksum and a signed build attestation. Details: [docs/SECURITY.md](../docs/SECURITY.md) ·
  audit: [docs/SECURITY_AUDIT.md](../docs/SECURITY_AUDIT.md)

**Responsible use:** download only what you own or are allowed to keep, and follow your school's
and each site's terms. Don't re-share recordings of other people.

## Repository layout
```
Setup.bat       build + install on your own PC (Python 3.10+ needed)
app/            program source
build_tools/    installer script, locked dependencies, tests
docs/           user guide, changelog, security, third-party notices
.github/        this page + the automated build (workflows/)
```

## License
© 2026 AKA. All rights reserved. **Freeware, not open source:** free to use and to share the
unmodified installer. No selling, modifying or rebranding. See [app/LICENSE.txt](../app/LICENSE.txt).
Third-party components keep their own licenses: [docs/THIRD_PARTY_NOTICES.txt](../docs/THIRD_PARTY_NOTICES.txt).
