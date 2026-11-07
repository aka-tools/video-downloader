VIDEO DOWNLOADER  V1
Copyright (c) 2026 AKA. All rights reserved.
Free to use and to share unmodified - see LICENSE.txt.
======================
Download Canvas/Panopto lecture recordings (and videos from YouTube, Vimeo and
1,000+ other sites) together with a timestamped transcript.


INSTALL  (one file, about 1 minute, no administrator rights needed)
-------
Double-click  VideoDownloader-Setup-V1.exe  and click Install.
"Video Downloader" appears in the Start menu (and on the Desktop if you choose).

   Windows may show "Windows protected your PC" because the app is not yet
   commercially signed. Click "More info" > "Run anyway".

Requirements: Windows 10/11 (64-bit) with Microsoft Edge (installed by default).


USE
---
First time only:  click "Sign in to Canvas", sign in normally in the window that
                  opens. It closes by itself when you're in.

Every time:       1. Copy the Canvas lecture page link from your browser.
                  2. Open Video Downloader (it pastes the link for you).
                  3. Click Download.

You get, in Downloads\Videos (changeable):
   * the lecture video (.mp4)
   * "<title>.srt" - subtitles with the same name as the video. Windows Media
     Player, Films & TV and VLC load it automatically: just press CC.
     (You don't open this file yourself. The subtitles are also inside the video.)
   * "<title> - transcript.txt" - bullet points with timestamps, e.g.
        • [00:12:30]  Rhino Inside lets Grasshopper run inside Revit...

Other Canvas schools: Account menu > Canvas address.
Public videos (YouTube etc.): set Login to "None (public videos)".


PRIVACY & SECURITY
------------------
* No telemetry, no accounts, no cloud. The app only contacts the links you paste,
  your Canvas/Panopto site, and - once a day, if enabled - GitHub to check for a
  newer version (no personal data is sent; turn it off under Help).
* You type your password into Canvas's own sign-in page - never into this app.
* The saved login is encrypted with Windows DPAPI: only your Windows account on
  your PC can read it. It is useless if copied elsewhere.
  Account menu > "Sign out and forget login" deletes it.
* During downloads the login is kept in memory only - never written in plain text.
* Uses its own private browser profile: your normal browser, passwords and
  history are never accessed.
* Only Canvas and Panopto cookies are kept; everything else is discarded.
* Only secure https:// links are accepted. The app never installs or runs
  anything it downloads.
* Data location (settings, encrypted login, logs):
      %LOCALAPPDATA%\VideoDownloader
  Logs never contain passwords or login cookies.

NEVER share your %LOCALAPPDATA%\VideoDownloader folder.

Responsible use: recordings are for your own study. They may include other
participants' faces and voices - don't upload or re-share them, and follow your
institution's rules on recordings.


UPDATES
-------
When a new version is out, the app shows "Version X is available". Click
"Get the update", download the new VideoDownloader-Setup .exe and run it.
Your settings and sign-in are kept.  Help > Check for updates checks on demand.


UNINSTALL
---------
Windows Settings > Apps > Installed apps > Video Downloader > Uninstall.
This removes the app, its shortcuts and your saved login. Downloaded videos are kept.


TROUBLESHOOTING
---------------
* "Canvas still asks for a login": Account > Sign in to Canvas, sign in fully
  (tick "Stay signed in" if offered), wait until your courses appear.
* "No captions available": that recording has no captions in Panopto.
* "Captions still refused" (YouTube): YouTube limits caption downloads. The video
  is saved anyway; download it again later to get the captions.
* Logs for support: File > Open log folder.
