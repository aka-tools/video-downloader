# Security policy — Video Downloader

## Supported versions
Only the latest release receives security fixes. Old versions should be uninstalled.

## Reporting a vulnerability
Please report privately. Do not open a public issue.
Use this repository's **Security** tab → **Report a vulnerability** (GitHub private
vulnerability reporting). Include:
- the version (Help → About),
- what you found and how to reproduce it.
You will get a reply within 7 days. Fixes for confirmed issues are published as a new
release on the releases page.

## Verifying a download
1. Download only from this repository's **Releases** page.
2. Compare the installer's SHA-256 with the `.sha256` file on the releases page
   (PowerShell: `Get-FileHash .\VideoDownloader-Setup-V1.exe`).
3. Right-click the installer > Properties > Details: publisher and copyright must read
   "AKA". Once code-signed, also check the Digital Signatures tab.
4. Builds made by the official pipeline can be verified with
   `gh attestation verify VideoDownloader-Setup-V1.exe -R <owner>/<repo>`.

## What the app does and does not do
- Runs as the normal user; needs no administrator rights; installs no services,
  drivers, scheduled tasks or browser extensions. The only registry entry is the
  standard per-user "Installed apps" uninstall entry (HKCU), removed on uninstall.
- Opens no network ports. Browser automation uses a private pipe, not a debug port.
- No telemetry, analytics, accounts or cloud storage. The optional daily update check
  asks GitHub for the latest version number only; it never downloads or runs anything.
- Saved login: encrypted with Windows DPAPI (current user only), limited to the
  configured Canvas site and Panopto. Sign out deletes it.
- Never executes downloaded files; never disables HTTPS certificate checks.
