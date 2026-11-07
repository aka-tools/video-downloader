# Copyright (c) 2026 AKA. All rights reserved.
# Part of Video Downloader - see LICENSE.txt. Unauthorised copying or modification is prohibited.
"""
Video Downloader - download lecture recordings and online videos with transcripts.

* Canvas / Panopto: sign in once, paste the Canvas lecture page link, click Download.
* Other sites: YouTube, Vimeo and 1,000+ others via yt-dlp.

Privacy & security: see SECURITY in README.txt. In short - no telemetry, the saved
login is encrypted with Windows DPAPI, login cookies are never written to disk in
plain text, and the app never installs or runs anything it downloads.
"""
import json
import logging
import logging.handlers
import os
import queue
import re
import shutil
# subprocess is only used to open a folder on non-Windows developer machines
import subprocess  # nosec B404
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

import imageio_ffmpeg
import yt_dlp

import canvas_helper
import transcript
import updater
import webbrowser

APP_NAME = "Video Downloader"
APP_VERSION = "1.0.0"   # internal number (used by the update check)
APP_LABEL = "V1"         # what users see - stays V1 until the owner decides otherwise
APP_AUTHOR = "AKA"
APP_COPYRIGHT = f"© 2026 {APP_AUTHOR}. All rights reserved."
DATA_DIR = canvas_helper.DATA_DIR
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
LOG_DIR = os.path.join(DATA_DIR, "logs")
DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "Videos")
DEFAULT_CANVAS = "canvas.e-zigurat.com"
MIN_FREE_GB = 3

QUALITY_OPTIONS = {
    "Best available": "bestvideo+bestaudio/best",
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p (smaller files)": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "Audio only (MP3)": "bestaudio/best",
}
AUTO = "Automatic (Canvas sign-in)"
LOGIN_OPTIONS = [AUTO, "None (public videos)", "Firefox", "cookies.txt file…"]


def resource(name):
    return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), name)


# ---------- logging (local file only, never contains cookies) ----------
os.makedirs(LOG_DIR, exist_ok=True)
logger = logging.getLogger("vd")
logger.setLevel(logging.INFO)
_h = logging.handlers.RotatingFileHandler(os.path.join(LOG_DIR, "app.log"), maxBytes=1_000_000,
                                          backupCount=3, encoding="utf-8")
_h.setFormatter(logging.Formatter("%(asctime)s  %(levelname)s  %(message)s"))
logger.addHandler(_h)


def redact(url):
    """Hide query strings in logs (some video links carry access tokens); keep Panopto/YouTube ids."""
    base, _, query = url.partition("?")
    if not query:
        return url
    keep = [p for p in query.split("&") if p.split("=")[0].lower() in ("id", "v", "module_item_id")]
    return base + ("?" + "&".join(keep) if keep else "?…")


def load_settings():
    s = {"folder": DEFAULT_DIR, "quality": "Best available", "login": AUTO,
         "subs": True, "canvas_host": DEFAULT_CANVAS,
         "check_updates": True, "last_update_check": 0}
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            s.update({k: v for k, v in json.load(f).items() if k in s})
    except (OSError, ValueError):
        pass
    if s["quality"] not in QUALITY_OPTIONS:
        s["quality"] = "Best available"
    if s["login"] not in LOGIN_OPTIONS or s["login"].startswith("cookies.txt"):
        s["login"] = AUTO
    if not canvas_helper.valid_host(s["canvas_host"]):
        s["canvas_host"] = DEFAULT_CANVAS
    return s


def save_settings(s):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2)
    except OSError:
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.title(f"{APP_NAME}  {APP_LABEL}   ·   {APP_COPYRIGHT}")
        self.geometry("820x640")
        self.minsize(680, 560)
        try:
            self.iconbitmap(resource("icon.ico"))
        except tk.TclError:
            pass
        self.msgs = queue.Queue()
        self.busy = False
        self.cookie_file = ""
        self._style()
        self._menu()
        self._build_ui()
        self._refresh_account()
        self._startup_hints()
        if self.settings.get("check_updates", True) and updater.due(self.settings.get("last_update_check")):
            self.after(3000, self._check_updates)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll)

    # ---------- look & feel ----------
    def _style(self):
        st = ttk.Style(self)
        for theme in ("vista", "winnative", "clam"):
            if theme in st.theme_names():
                st.theme_use(theme)
                break
        st.configure("Title.TLabel", font=("Segoe UI Semibold", 15))
        st.configure("Sub.TLabel", font=("Segoe UI", 9), foreground="#666")
        st.configure("Primary.TButton", font=("Segoe UI Semibold", 10), padding=(18, 6))
        st.configure("Ok.TLabel", foreground="#1a7f37")
        st.configure("Warn.TLabel", foreground="#b35900")

    def _menu(self):
        m = tk.Menu(self)
        f = tk.Menu(m, tearoff=0)
        f.add_command(label="Open download folder", command=self._open_folder)
        f.add_command(label="Open log folder", command=lambda: self._open_path(LOG_DIR))
        f.add_separator()
        f.add_command(label="Exit", command=self._on_close)
        m.add_cascade(label="File", menu=f)
        a = tk.Menu(m, tearoff=0)
        a.add_command(label="Sign in to Canvas…", command=self._manual_sign_in)
        a.add_command(label="Sign out and forget login", command=self._sign_out)
        a.add_separator()
        a.add_command(label="Canvas address…", command=self._set_canvas_host)
        m.add_cascade(label="Account", menu=a)
        h = tk.Menu(m, tearoff=0)
        h.add_command(label="How to use", command=self._help)
        h.add_command(label="Privacy & security", command=self._security)
        h.add_command(label="Check for updates", command=lambda: self._check_updates(manual=True))
        self.auto_updates = tk.BooleanVar(value=self.settings.get("check_updates", True))
        h.add_checkbutton(label="Check for updates automatically", variable=self.auto_updates,
                          command=self._toggle_auto_updates)
        h.add_separator()
        h.add_command(label="License", command=self._license)
        h.add_command(label="About", command=self._about)
        m.add_cascade(label="Help", menu=h)
        self.config(menu=m)

    def _build_ui(self):
        root = ttk.Frame(self, padding=14)
        root.pack(fill="both", expand=True)

        head = ttk.Frame(root)
        head.pack(fill="x")
        ttk.Label(head, text=APP_NAME, style="Title.TLabel").pack(side="left")
        self.account_lbl = ttk.Label(head, text="")
        self.account_lbl.pack(side="right")
        ttk.Label(root, text="Paste a Canvas lecture page link (or any video link) and click Download.",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 8))
        self.update_bar = ttk.Frame(root)  # shown only when a newer version exists
        self.update_lbl = ttk.Label(self.update_bar, text="", style="Ok.TLabel")
        self.update_lbl.pack(side="left")
        self.update_btn = ttk.Button(self.update_bar, text="Get the update")
        self.update_btn.pack(side="left", padx=8)
        ttk.Button(self.update_bar, text="Later", command=self.update_bar.pack_forget).pack(side="left")
        self._first_section = None

        lf = ttk.LabelFrame(root, text=" Links (one per line) ", padding=8)
        lf.pack(fill="x")
        self._first_section = lf
        self.urls = tk.Text(lf, height=5, wrap="none", font=("Consolas", 10), relief="flat",
                            highlightthickness=1, highlightbackground="#ccc")
        self.urls.pack(fill="x")
        row = ttk.Frame(lf)
        row.pack(fill="x", pady=(6, 0))
        ttk.Button(row, text="Paste", command=self._paste).pack(side="left")
        ttk.Button(row, text="Clear", command=lambda: self.urls.delete("1.0", "end")).pack(side="left", padx=6)

        of = ttk.LabelFrame(root, text=" Options ", padding=8)
        of.pack(fill="x", pady=8)
        of.columnconfigure(1, weight=1)
        of.columnconfigure(3, weight=1)
        ttk.Label(of, text="Quality").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.quality = ttk.Combobox(of, values=list(QUALITY_OPTIONS), state="readonly")
        self.quality.set(self.settings["quality"])
        self.quality.grid(row=0, column=1, sticky="ew")
        ttk.Label(of, text="Login").grid(row=0, column=2, sticky="w", padx=(14, 6))
        self.login = ttk.Combobox(of, values=LOGIN_OPTIONS, state="readonly")
        self.login.set(self.settings["login"])
        self.login.grid(row=0, column=3, sticky="ew")
        self.login.bind("<<ComboboxSelected>>", self._login_changed)

        self.subs = tk.BooleanVar(value=self.settings["subs"])
        ttk.Checkbutton(of, text="Save transcript (timestamped bullet points) + subtitles in the video",
                        variable=self.subs).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.playlist = tk.BooleanVar(value=False)
        ttk.Checkbutton(of, text="Download whole playlist", variable=self.playlist).grid(
            row=1, column=2, columnspan=2, sticky="w", padx=(14, 0), pady=(8, 0))

        ttk.Label(of, text="Save to").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.folder = tk.StringVar(value=self.settings["folder"])
        ff = ttk.Frame(of)
        ff.grid(row=2, column=1, columnspan=3, sticky="ew", pady=(8, 0))
        ttk.Entry(ff, textvariable=self.folder).pack(side="left", fill="x", expand=True)
        ttk.Button(ff, text="Browse…", command=self._browse).pack(side="left", padx=(6, 0))
        ttk.Button(ff, text="Open", command=self._open_folder).pack(side="left", padx=(6, 0))

        act = ttk.Frame(root)
        act.pack(fill="x", pady=(2, 6))
        self.dl_btn = ttk.Button(act, text="Download", style="Primary.TButton", command=self._start)
        self.dl_btn.pack(side="left")
        self.signin_btn = ttk.Button(act, text="Sign in to Canvas", command=self._manual_sign_in)
        self.signin_btn.pack(side="left", padx=8)

        self.status = tk.StringVar(value="Ready.")
        ttk.Label(root, textvariable=self.status).pack(anchor="w")
        self.progress = ttk.Progressbar(root, maximum=100)
        self.progress.pack(fill="x", pady=(4, 8))

        lg = ttk.LabelFrame(root, text=" Activity ", padding=6)
        lg.pack(fill="both", expand=True)
        self.log = tk.Text(lg, height=8, state="disabled", wrap="word", font=("Consolas", 9),
                           relief="flat", bg="#fafafa")
        sb = ttk.Scrollbar(lg, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True)

    # ---------- small helpers ----------
    def _startup_hints(self):
        try:
            clip = self.clipboard_get().strip()
            if re.match(r"^https://\S+$", clip):
                self.urls.insert("end", clip + "\n")
                self._write_log("Pasted the link from your clipboard.")
        except tk.TclError:
            pass
        if self.login.get() == AUTO and not canvas_helper.is_signed_in():
            self._write_log("First time? Click 'Sign in to Canvas' once. After that, just paste and Download.")
        else:
            self._write_log("Ready.")

    def _refresh_account(self):
        if canvas_helper.is_signed_in():
            self.account_lbl.configure(text=f"● Signed in · {self.settings['canvas_host']}", style="Ok.TLabel")
        else:
            self.account_lbl.configure(text="● Not signed in to Canvas", style="Warn.TLabel")

    def _set_busy(self, busy):
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.dl_btn.configure(state=state)
        self.signin_btn.configure(state=state)

    def _paste(self):
        try:
            self.urls.insert("end", self.clipboard_get().strip() + "\n")
        except tk.TclError:
            pass

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self.folder.get())
        if d:
            self.folder.set(os.path.normpath(d))

    def _open_path(self, path):
        os.makedirs(path, exist_ok=True)
        if sys.platform.startswith("win"):
            # opens our own local folder in Explorer - no user-supplied command
            os.startfile(path)  # nosec B606
        else:
            subprocess.Popen(["xdg-open", path])  # nosec B603 B607

    def _open_folder(self):
        self._open_path(self.folder.get())

    def _write_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        logger.info(text.strip())

    def _persist(self):
        self.settings.update(folder=self.folder.get(), quality=self.quality.get(),
                             login=self.login.get() if not self.login.get().startswith("cookies") else AUTO,
                             subs=self.subs.get())
        save_settings(self.settings)

    def _on_close(self):
        if self.busy and not messagebox.askyesno(APP_NAME, "A download is running. Quit anyway?"):
            return
        self._persist()
        self.destroy()

    # ---------- account ----------
    def _manual_sign_in(self):
        if self.busy:
            return
        self._set_busy(True)

        def run():
            try:
                canvas_helper.sign_in(self.settings["canvas_host"], lambda t: self.msgs.put(("log", t)))
            except Exception as e:  # noqa: BLE001
                self.msgs.put(("log", f"✘ Sign-in not completed: {self._short(e)}"))
            self.msgs.put(("idle",))
        threading.Thread(target=run, daemon=True).start()

    def _sign_out(self):
        if self.busy:
            return
        if messagebox.askyesno(APP_NAME, "Sign out and delete the saved Canvas login from this PC?"):
            canvas_helper.sign_out()
            self._refresh_account()
            self._write_log("Signed out. The saved login was deleted from this PC.")

    def _set_canvas_host(self):
        v = simpledialog.askstring(APP_NAME, "Canvas address (for example canvas.e-zigurat.com):",
                                   initialvalue=self.settings["canvas_host"], parent=self)
        if not v:
            return
        v = re.sub(r"^https?://", "", v.strip().lower()).strip("/")
        if not canvas_helper.valid_host(v):
            messagebox.showerror(APP_NAME, "That doesn't look like a valid web address.")
            return
        if v != self.settings["canvas_host"]:
            canvas_helper.sign_out()  # never reuse a login across sites
            self.settings["canvas_host"] = v
            save_settings(self.settings)
            self._refresh_account()
            self._write_log(f"Canvas address set to {v}. Please sign in again.")

    def _login_changed(self, _event=None):
        if self.login.get().startswith("cookies.txt"):
            f = filedialog.askopenfilename(title="Choose cookies.txt",
                                           filetypes=[("Cookies file", "*.txt"), ("All files", "*.*")])
            if f:
                self.cookie_file = f
                self._write_log("Using the selected cookies file (it is not copied or stored).")
            else:
                self.login.set(AUTO)
        elif self.login.get() == "Firefox":
            self._write_log("Using your Firefox login. Sign in to the site in Firefox first.")

    # ---------- help ----------
    def _help(self):
        messagebox.showinfo("How to use", (
            "Canvas lectures (Panopto)\n"
            "1. Click 'Sign in to Canvas' once and sign in. The window closes by itself.\n"
            "2. Copy the Canvas lecture page link from your browser.\n"
            "3. Open the app (it pastes the link for you) and click Download.\n\n"
            "Other videos (YouTube, Vimeo…)\n"
            "Set Login to 'None (public videos)', paste the link and click Download.\n\n"
            "Files are saved to your 'Save to' folder: the video (.mp4) with built-in subtitles "
            "(press CC in your player) and a transcript (.txt) as timestamped bullet points."))

    def _security(self):
        messagebox.showinfo("Privacy & security", (
            "• No telemetry: the app only contacts the sites you paste, your Canvas/Panopto, and "
            "(once a day, if enabled) GitHub to check for a newer version - no personal data is sent.\n"
            "• Your Canvas password is typed into Canvas's own page, never into this app.\n"
            "• The saved login is encrypted with Windows DPAPI: only your Windows account on this "
            "PC can read it. Sign out (Account menu) deletes it.\n"
            "• Login cookies are kept in memory during downloads - never written as plain text.\n"
            "• Uses a separate, private browser profile - your normal browser is never touched.\n"
            "• Never installs or runs anything it downloads.\n\n"
            "Please use recordings for your own study only and follow your institution's policy - "
            "they may contain other participants' images and voices. Don't re-share them."))

    # ---------- updates ----------
    def _toggle_auto_updates(self):
        self.settings["check_updates"] = bool(self.auto_updates.get())
        save_settings(self.settings)

    def _check_updates(self, manual=False):
        if not updater.is_configured():
            if manual:
                messagebox.showinfo(APP_NAME, "Update checks aren't set up for this copy yet.")
            return

        def run():
            try:
                res = updater.check(APP_VERSION)
                self.msgs.put(("update", res, manual, None))
            except Exception as e:  # noqa: BLE001
                self.msgs.put(("update", None, manual, self._short(e)))
        threading.Thread(target=run, daemon=True).start()

    def _show_update(self, res, manual, err):
        self.settings["last_update_check"] = time.time()
        save_settings(self.settings)
        if err:
            logger.info("Update check failed: %s", err)
            if manual:
                messagebox.showwarning(APP_NAME, "Couldn't check for updates right now. "
                                                 "Check your internet connection and try again.")
            return
        if not res:
            if manual:
                messagebox.showinfo(APP_NAME, f"You have the latest version ({APP_LABEL}).")
            return
        version, page = res
        self._write_log(f"A new version is available: {version}")
        self.update_lbl.configure(text=f"⬆  A new version ({version}) is available (you have {APP_LABEL}).")
        self.update_btn.configure(command=lambda: self._open_release(page))
        self.update_bar.pack(fill="x", pady=(0, 8), before=self._first_section)

    def _open_release(self, page):
        if page.startswith("https://github.com/"):
            webbrowser.open(page)
            messagebox.showinfo(APP_NAME, "Download 'VideoDownloader-Setup' (.exe) from the page that opened "
                                          "and run it. Your settings and sign-in are kept.")

    def _license(self):
        path = resource("LICENSE.txt")
        if os.path.exists(path):
            os.startfile(path) if sys.platform.startswith("win") else messagebox.showinfo(APP_NAME, path)  # nosec B606
        else:
            messagebox.showinfo("License", f"{APP_COPYRIGHT}\nSee LICENSE.txt in the install folder.")

    def _about(self):
        messagebox.showinfo("About", f"{APP_NAME} {APP_LABEL}\n{APP_COPYRIGHT}\n\n"
                                     f"Free to use and share unmodified (see License).\n"
                                     f"Powered by yt-dlp, FFmpeg and Playwright (own licenses).\n"
                                     f"Settings & logs: {DATA_DIR}")

    # ---------- download ----------
    @staticmethod
    def _short(e):
        return (str(e).strip().splitlines() or [type(e).__name__])[0][:220]

    def _start(self):
        if self.busy:
            return
        raw = [u.strip() for u in self.urls.get("1.0", "end").splitlines() if u.strip()]
        links = [u for u in raw if re.match(r"^https://\S+$", u)]
        skipped = [u for u in raw if u not in links]
        for u in skipped:
            self._write_log(f"Skipped (only secure https:// links are allowed): {redact(u)[:80]}")
        if not links:
            messagebox.showwarning(APP_NAME, "Paste at least one https:// link first.")
            return
        folder = os.path.abspath(self.folder.get())
        try:
            os.makedirs(folder, exist_ok=True)
            free_gb = shutil.disk_usage(folder).free / 1024 ** 3
        except OSError as e:
            messagebox.showerror(APP_NAME, f"Can't use that folder:\n{e}")
            return
        if free_gb < MIN_FREE_GB and not messagebox.askyesno(
                APP_NAME, f"Only {free_gb:.1f} GB free on that drive. Lectures can be 1-3 GB each.\n"
                          f"Continue anyway?"):
            return
        self._persist()
        self._set_busy(True)
        threading.Thread(target=self._worker, args=(links, folder), daemon=True).start()

    def _hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            pct = done / total * 100 if total else 0
            speed = (d.get("_speed_str") or "").strip()
            eta = (d.get("_eta_str") or "").strip()
            self.msgs.put(("progress", pct, f"Downloading…  {pct:.0f}%   {speed}   ETA {eta}"))
        elif d["status"] == "finished":
            self.msgs.put(("progress", 100, "Processing…"))

    def _worker(self, links, folder):
        label = self.quality.get()
        login = self.login.get()
        canvas_host = self.settings["canvas_host"]
        log = lambda t: self.msgs.put(("log", t))  # noqa: E731
        opts = {
            "format": QUALITY_OPTIONS[label],
            "outtmpl": os.path.join(folder, "%(title).150s [%(id)s].%(ext)s"),
            "paths": {"temp": folder},
            "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
            "noplaylist": not self.playlist.get(),
            "progress_hooks": [self._hook],
            "windowsfilenames": True,
            "quiet": True,
            "no_warnings": True,
            "retries": 5,
            "nocheckcertificate": False,       # always verify HTTPS certificates
            "allow_unplayable_formats": False,  # never try DRM-protected streams
            "fragment_retries": 10,
            "concurrent_fragment_downloads": 3,
        }
        if login.startswith("cookies.txt") and self.cookie_file:
            opts["cookiefile"] = self.cookie_file
        elif login == "Firefox":
            opts["cookiesfrombrowser"] = ("firefox",)
        if self.subs.get():
            opts.update({"writesubtitles": True, "writeautomaticsub": True,
                         "subtitleslangs": ["all", "-live_chat"], "subtitlesformat": "srt/vtt/best"})
        if label.startswith("Audio"):
            opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
                                       "preferredquality": "192"}]
        else:
            opts["merge_output_format"] = "mp4"
            if self.subs.get():
                # put the subtitles INSIDE the .mp4 (turn on with the CC button in any player);
                # keep the file for a moment so we can build the readable transcript from it
                opts["postprocessors"] = [
                    # YouTube etc. deliver .vtt - convert to .srt, the format every Windows player reads
                    {"key": "FFmpegSubtitlesConvertor", "format": "srt", "when": "before_dl"},
                    {"key": "FFmpegEmbedSubtitle", "already_have_subtitle": True},
                ]

        ok = 0
        for i, url in enumerate(links, 1):
            log(f"[{i}/{len(links)}] {redact(url)}")
            try:
                targets, cookies = [url], []
                host = canvas_helper.host_of(url)
                if login == AUTO and (host == canvas_host or canvas_helper.is_panopto_host(host)):
                    self.msgs.put(("progress", 0, "Finding the video…"))
                    try:
                        targets, cookies = canvas_helper.resolve(url, canvas_host, log)
                    except canvas_helper.NeedLogin:
                        canvas_helper.sign_in(canvas_host, log)
                        self.msgs.put(("account",))
                        try:
                            targets, cookies = canvas_helper.resolve(url, canvas_host, log)
                        except canvas_helper.NeedLogin:
                            raise RuntimeError("Canvas still asks for a login - use 'Sign in to Canvas' "
                                               "and sign in fully, then try again.") from None
                for target in targets:
                    run_opts = dict(opts)
                    if self.subs.get() and not canvas_helper.is_panopto_host(canvas_helper.host_of(target)):
                        # YouTube & co. offer ~100 auto-translated tracks and rate-limit them (HTTP 429):
                        # ask for exactly original + English + Arabic, with a pause between requests
                        run_opts["subtitleslangs"] = [".*-orig", "en", "ar"]
                        run_opts["sleep_interval_subtitles"] = 3
                    info = self._download(target, run_opts, cookies, log)
                    title = (info or {}).get("title", "video")
                    log(f"   ✔ Saved: {title}")
                    if self.subs.get() and info:
                        self._make_transcripts(info, log)
                cookies.clear()
                ok += 1
            except Exception as e:  # noqa: BLE001
                msg = self._short(e)
                log(f"   ✘ Failed: {msg}")
                low = msg.lower()
                if any(k in low for k in ("login", "sign in", "cookie", "403", "401")):
                    log("     Tip: this needs your login. Use 'Sign in to Canvas' (Canvas links) or "
                        "choose Firefox under Login (other sites).")
                elif "unsupported url" in low:
                    log("     Tip: no video found on this page. Paste the video's own link instead.")
        self.msgs.put(("done", ok, len(links)))

    def _download(self, target, run_opts, cookies, log):
        """
        Download one video. Captions must never cost the user the video:
          1st try  - video + requested captions
          2nd try  - video + original-language captions only (after a pause)
          3rd try  - video without captions
        """
        def attempt(o):
            with yt_dlp.YoutubeDL(o) as ydl:
                if cookies:
                    canvas_helper.add_cookies_to_jar(ydl.cookiejar, cookies)  # in memory only
                return ydl.extract_info(target, download=True)

        try:
            return attempt(run_opts)
        except yt_dlp.utils.DownloadError as e:
            if "subtitles" not in str(e).lower() or not run_opts.get("writesubtitles"):
                raise
            busy = "429" in str(e)
            log("     ⚠ The site refused the captions" + (" (too many requests)" if busy else "")
                + " - retrying with the original-language track only…")
        time.sleep(20 if busy else 3)
        retry = dict(run_opts, subtitleslangs=[".*-orig", "en"], sleep_interval_subtitles=5)
        try:
            return attempt(retry)
        except yt_dlp.utils.DownloadError as e:
            if "subtitles" not in str(e).lower():
                raise
            log("     ⚠ Captions still refused - saving the video without captions. "
                "Try again later to get them.")
        plain = {k: v for k, v in run_opts.items()
                 if k not in ("writesubtitles", "writeautomaticsub", "subtitleslangs",
                              "subtitlesformat", "sleep_interval_subtitles")}
        plain["postprocessors"] = [p for p in run_opts.get("postprocessors", [])
                                   if "Subtitle" not in p.get("key", "")]
        return attempt(plain)

    def _make_transcripts(self, info, log):
        """
        For each downloaded video:
          * "<video name> - transcript.txt"  - timestamped bullet points
          * "<video name>.srt"               - same name as the video, so Windows Media Player,
                                               Films & TV and VLC switch on CC automatically
        """
        entries = info.get("entries") or [info]
        for entry in entries:
            entry = entry or {}
            subs = entry.get("requested_subtitles") or {}
            files = [(lang, s.get("filepath")) for lang, s in subs.items()
                     if s.get("filepath") and os.path.exists(s.get("filepath"))]
            # drop auto-copies of the original track (e.g. "en" next to "en-orig")
            for lang, path in list(files):
                if f"{lang}-orig" in subs:
                    os.remove(path)
                    files.remove((lang, path))
            if not files:
                log("     ⚠ No captions available for this video - no subtitles or transcript.")
                continue

            # best track first: original language, then English, then Arabic, then anything
            def rank(item):
                lang = item[0].lower()
                return (0 if lang.endswith("-orig") else 1 if lang.startswith("en") else
                        2 if lang.startswith("ar") else 3)
            files.sort(key=rank)

            video = ((entry.get("requested_downloads") or [{}])[0].get("filepath")
                     or entry.get("filepath") or "")
            base = os.path.splitext(video)[0] if video else os.path.splitext(files[0][1])[0]

            for n, (lang, path) in enumerate(files):
                try:
                    if n == 0:
                        text = transcript.to_bullets(path, title=entry.get("title", ""))
                        with open(base + " - transcript.txt", "w", encoding="utf-8") as f:
                            f.write(text)
                        log(f"   ✔ Transcript: {os.path.basename(base)} - transcript.txt")
                        if path.lower().endswith(".srt"):
                            os.replace(path, base + ".srt")
                            log("   ✔ Subtitles: inside the video + matching .srt "
                                "(CC turns on automatically in Media Player / VLC)")
                        else:
                            os.remove(path)
                            log("   ✔ Subtitles: inside the video")
                    else:
                        os.remove(path)  # extra languages stay inside the video only
                except Exception as e:  # noqa: BLE001
                    log(f"   ✘ Subtitles/transcript problem: {self._short(e)}")

    def _poll(self):
        try:
            while True:
                m = self.msgs.get_nowait()
                if m[0] == "progress":
                    self.progress["value"] = m[1]
                    self.status.set(m[2])
                elif m[0] == "log":
                    self._write_log(m[1])
                elif m[0] == "update":
                    self._show_update(m[1], m[2], m[3])
                elif m[0] == "account":
                    self._refresh_account()
                elif m[0] == "idle":
                    self._set_busy(False)
                    self._refresh_account()
                elif m[0] == "done":
                    self._set_busy(False)
                    self._refresh_account()
                    self.progress["value"] = 100 if m[1] else 0
                    self.status.set(f"Finished: {m[1]} of {m[2]} downloaded.")
                    self._write_log(f"Finished: {m[1]}/{m[2]} successful.\n")
        except queue.Empty:
            pass
        self.after(100, self._poll)


if __name__ == "__main__":
    App().mainloop()
