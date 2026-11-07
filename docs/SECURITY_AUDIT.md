# Video Downloader V1 — Pre-launch Security Audit

**Date:** 2026-11-07  **Scope:** source code, build pipeline, installer/uninstaller, bundled
third-party components, data handling. **Assumed use:** free public download and install.

## 1. Verdict

**Ready for colleagues and small-scale sharing. Two blocking items remain for a public
launch** (code signing and an update channel; see §6). No high- or medium-severity code
issues were found; all fixable findings were fixed in V1.

No software can honestly be called "unhackable". The goal is that installing this app
does **not add a new way in** to the user's PC, and that it protects the one sensitive
item it holds (the Canvas login). Both are met, with the residual risks listed in §5.

## 2. Tests run

| Test | Tool | Result |
|---|---|---|
| Static code analysis (796 lines) | Bandit 1.9 | 0 high, 0 medium. 3 low (intentional silent fallbacks, accepted) |
| Known-vulnerability scan, all 16 pinned packages | pip-audit (PyPI advisory DB) | **No known vulnerabilities** |
| Known-vulnerability scan | OSV database | Not run, blocked from the audit sandbox. Runs in the release pipeline instead |
| Bundled binaries | Manual inspection | Node.js 24.22.1 (current LTS line), FFmpeg 9.0.x GPL build |
| Secrets / personal data in shipped files | Pattern scan | None found |
| Windows availability of every locked package | Hash-verified download | All 13 Windows packages available as pre-built wheels |
| Code review of installer, uninstaller, build script | Manual | 6 findings, all fixed (§3) |
| Logic tests: cookie scoping, host allow-list, log redaction, transcript parser | Unit tests | Pass |

**Not tested here** (needs Windows): the built .exe itself, antivirus behaviour, and a live
Canvas sign-in. Do a final smoke test on a clean Windows PC before public release.

## 3. Findings and fixes

| # | Severity | Finding | Fix in V1 |
|---|---|---|---|
| 1 | High (supply chain) | Dependencies not pinned; a compromised future release would enter the next build | `requirements.lock`: exact versions + SHA-256 hashes, `--require-hashes`, pre-built wheels only |
| 2 | Medium | Installer/uninstaller used `%LOCALAPPDATA%` unchecked; if empty, mirror/delete would target the wrong folder | Hard guard: aborts with "Nothing was changed" |
| 3 | Medium | No integrity check at install time | Single installer .exe with publisher/copyright details; integrity is proven by the published SHA-256 and the build attestation now, and by code signing for the public launch |
| 4 | Medium | Build environment reused between builds (stale or tampered packages could persist) | Fresh isolated environment on every build |
| 5 | Low | Full links written to logs; some video links carry access tokens | Query strings redacted (only video ids kept) |
| 6 | Low | Hidden sign-in browser relied on defaults | Explicit lockdown: no permissions, permission prompts denied, downloads blocked, service workers blocked, invalid certificates refused, background networking off |
| — | Fixed in 1.0.0 | Saved login in plain text; cookies in temp files; third-party mirrors with TLS checks off; runtime `pip install` | DPAPI encryption; in-memory cookies; official PyPI only; no runtime installs |

## 4. Security properties (verified in code)

- **No elevation:** per-user install (Inno Setup, `PrivilegesRequired=lowest`), no admin rights, no services, drivers, scheduled tasks or browser extensions; only the standard per-user uninstall entry (HKCU).
- **No attack surface on the network:** opens no listening ports; browser automation uses a local pipe, not a remote-debugging port.
- **No telemetry:** contacts only the links the user pastes plus the configured Canvas site and Panopto.
- **Credentials:** the password is typed into Canvas's own page only. The saved session is DPAPI-encrypted (current Windows user, this PC), scoped to Canvas and Panopto cookies, and deleted on sign-out or uninstall. The plain-text file from older builds is purged automatically.
- **Isolation:** a separate browser profile; the user's real browser, passwords and history are never read (unless the user picks the optional Firefox login mode).
- **Input handling:** https-only links; automation is restricted to the configured Canvas host and `*.panopto.com` / `*.panopto.eu`; the Canvas address is validated; file names are sanitised by yt-dlp (Windows-safe).
- **No code execution from content:** downloaded files are never opened or executed; no yt-dlp `--exec` or external downloaders; certificate checks are always on; DRM streams are never attempted.
- **Hardware safety:** free-disk-space check before downloads; per-user files only; bounded rotating logs (3 × 1 MB).

## 5. Residual risks (accepted, documented)

1. **Malware already running as the user** can read anything that user can, including the DPAPI-protected login. No user-level app can prevent this. Mitigation: sign out when not needed.
2. **Malformed media parsed by FFmpeg.** FFmpeg only remuxes (no re-encoding), which limits exposure but doesn't remove it. Mitigation: ship updates when FFmpeg releases fixes.
3. **User-writable install folder** (standard for per-user apps, e.g. VS Code's user installer): another process running as the same user could replace files. The install-time checksum detects tampering only at install.
4. **Unsigned executable:** SmartScreen warns, and users can't cryptographically confirm the publisher (see §6).
5. **Site changes:** Canvas, Panopto or video sites can change. That breaks features but has no security impact.

## 6. Before a PUBLIC free launch (blocking)

1. **Code-sign the .exe** (e.g. Azure Trusted Signing, or an OV/EV certificate). This removes the SmartScreen warning and proves the publisher.
2. **Publish through the included GitHub Actions pipeline** (`.github/workflows/release.yml`) ✅ ready: Actions → "Build & release" → Run workflow. It builds on a clean Microsoft-hosted Windows machine (never a personal PC), re-runs the scans, and publishes the checksum plus a signed build-provenance attestation.
3. **Update channel:** ✅ built into V1 (`updater.py`). The official GitHub build stamps the repository in automatically; re-release at least monthly.
4. **Licensing:** keep `THIRD_PARTY_NOTICES.txt` in every package (FFmpeg is GPL v3); ✅ freeware EULA in `app/LICENSE.txt`.
5. **Terms and privacy:** publish the privacy statement (no data collected). Check that public distribution of a tool aimed at Canvas/Panopto is acceptable under your institution's and Panopto's terms. Users must only download recordings they are permitted to keep.
6. **Security contact:** ✅ GitHub private vulnerability reporting (enable it in the repo: Settings → Security → Private vulnerability reporting). No email is published.

## 7. Maintenance routine

- **Monthly:** regenerate `requirements.lock` (`uv pip compile … --generate-hashes`), run `pip-audit`, bump the patch version, rebuild, and release.
- **On any advisory** for yt-dlp, FFmpeg, Playwright/Node.js or Python: release a patch within 7 days.

## 8. Addendum — single-file installer, ownership
- Distribution is now ONE file, `VideoDownloader-Setup-V1.exe` (Inno Setup, LZMA2), installed per-user with a standard uninstaller under Settings > Apps.
- The uninstaller also deletes the saved login, the private browser profile, settings and logs (`%LOCALAPPDATA%\VideoDownloader`). Downloaded videos are never touched.
- Ownership: copyright notices in every source file, the .exe version resource (Properties > Details), the installer, the About box and LICENSE.txt (freeware EULA).
- Because a single installer can't carry its own checksum file, verification relies on the SHA-256 and attestation published with each release, and on code signing (still required before a public launch).
