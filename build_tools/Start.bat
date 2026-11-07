@echo off
rem Developer mode: run Video Downloader from source without building.
cd /d "%~dp0.."
if not exist "_build\env\Scripts\python.exe" (
    mkdir _build 2>nul & attrib +h _build >nul 2>&1
    python -m venv _build\env
)
"_build\env\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check --require-hashes --only-binary=:all: -r build_tools\requirements.lock
start "" "_build\env\Scripts\pythonw.exe" app\video_downloader.py
