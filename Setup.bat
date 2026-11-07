@echo off
rem Copyright (c) 2026 AKA. All rights reserved.
setlocal
title Video Downloader V1 - build the installer
cd /d "%~dp0"

rem Folder layout:  app\ (program)  build_tools\ (build scripts)  docs\ (documents)
rem Temporary build files go to the hidden _build\ folder and are removed afterwards.
set "ROOT=%CD%"
set "WORK=%ROOT%\_build"

echo ============================================================
echo   Video Downloader V1 - one-click build
echo   Creates ONE file to share:  VideoDownloader-Setup-V1.exe
echo   and installs it on this PC.
echo ============================================================
echo.

set "STEP=checking Python"
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [X] Python 3.10 or newer is required ^(or "python" only opens the Microsoft Store^).
    echo     Install it from https://www.python.org/downloads/  and tick "Add Python to PATH",
    echo     then double-click Setup.bat again.
    goto :fail
)
for /f "delims=" %%P in ('python -c "import platform; print(platform.python_version())"') do echo Using Python %%P

rem ---- 1. fresh, isolated build environment (hidden _build folder) ----
set "STEP=1/5 preparing the build environment"
echo [1/5] Preparing a fresh, isolated build environment...
taskkill /im VideoDownloader.exe /f >nul 2>&1
if exist "%WORK%" rmdir /s /q "%WORK%"
mkdir "%WORK%"
attrib +h "%WORK%" >nul 2>&1
python -m venv "%WORK%\env"
if errorlevel 1 goto :fail
set "PY=%WORK%\env\Scripts\python.exe"

rem ---- 2. exact, hash-verified components from the official Python package index ----
set "STEP=2/5 downloading components"
echo [2/5] Downloading verified components...
"%PY%" -m pip install --disable-pip-version-check --retries 10 --timeout 120 --only-binary=:all: --require-hashes -r "%ROOT%\build_tools\requirements.lock"
if errorlevel 1 (
    echo.
    echo Could not download the components. Check your internet connection or try another
    echo network ^(e.g. a phone hotspot^). Company networks sometimes block pypi.org.
    goto :fail
)

rem ---- 3. build the app (with copyright + version in the .exe properties) ----
set "STEP=3/5 building the app"
echo [3/5] Building the app (2-4 minutes)...
"%PY%" "%ROOT%\build_tools\make_version_info.py" "%WORK%\version_info.txt" > "%WORK%\version.txt"
if errorlevel 1 goto :fail
for /f "usebackq tokens=1,2" %%V in ("%WORK%\version.txt") do (
    set "VER=%%V"
    set "LABEL=%%W"
)
if not defined VER (
    echo [X] Could not read the app version.
    goto :fail
)
echo     Building version %LABEL% ^(%VER%^)
"%PY%" -m PyInstaller --noconfirm --clean --onedir --windowed --log-level WARN ^
  --name VideoDownloader ^
  --distpath "%WORK%\dist" --workpath "%WORK%\work" --specpath "%WORK%" ^
  --icon "%ROOT%\app\icon.ico" ^
  --version-file "%WORK%\version_info.txt" ^
  --add-data "%ROOT%\app\icon.ico;." --add-data "%ROOT%\app\LICENSE.txt;." ^
  --collect-all imageio_ffmpeg ^
  --collect-all playwright ^
  --collect-submodules yt_dlp ^
  --hidden-import canvas_helper --hidden-import secure_store --hidden-import transcript --hidden-import updater ^
  "%ROOT%\app\video_downloader.py"
if errorlevel 1 goto :fail

rem ---- 4. pack everything into ONE installer .exe (Inno Setup) ----
set "STEP=4/5 creating the installer"
echo [4/5] Creating the single-file installer...
call :find_iscc
if not defined ISCC (
    echo     Installing the free Inno Setup compiler ^(one time, from the official winget catalog^)...
    winget install --id JRSoftware.InnoSetup -e --scope user --silent --accept-package-agreements --accept-source-agreements
    call :find_iscc
    if not defined ISCC (
        winget install --id JRSoftware.InnoSetup -e --silent --accept-package-agreements --accept-source-agreements
        call :find_iscc
    )
)
if not defined ISCC (
    echo [X] Inno Setup is needed to make the installer.
    echo     Install it from https://jrsoftware.org/isdl.php  then run Setup.bat again.
    goto :fail
)
if exist "VideoDownloader-Setup-*.exe" del /q "VideoDownloader-Setup-*.exe"
"%ISCC%" /Q /DAppVersion=%VER% /DAppLabel=%LABEL% "%ROOT%\build_tools\VideoDownloader.iss"
if errorlevel 1 (
    echo [X] The installer compiler reported an error ^(see the lines above^).
    goto :fail
)
if not exist "VideoDownloader-Setup-%LABEL%.exe" (
    echo [X] The installer file was not created.
    goto :fail
)
set "OUTEXE=VideoDownloader-Setup-%LABEL%.exe"
for /f "delims=" %%H in ('certutil -hashfile "%OUTEXE%" SHA256 ^| findstr /v ":"') do if not defined HASH set "HASH=%%H"
set "HASH=%HASH: =%"

rem ---- 5. install on this PC, then tidy up ----
set "STEP=5/5 installing on this PC"
echo [5/5] Installing on this PC...
"%OUTEXE%" /SILENT /SUPPRESSMSGBOXES /NORESTART /TASKS="desktopicon"
if errorlevel 1 (
    echo [X] Installing failed. Close Video Downloader if it is open and try again.
    echo     Your installer is ready anyway: %OUTEXE%
    goto :fail
)
rmdir /s /q "%WORK%" >nul 2>&1
start "" "%LOCALAPPDATA%\Programs\VideoDownloader\VideoDownloader.exe"

echo.
echo ============================================================
echo   All done! Video Downloader %LABEL% is installed.
echo.
echo   To share, send colleagues just ONE file (in this folder):
echo       %OUTEXE%
echo   They double-click it - that's all.
echo.
echo   SHA-256 fingerprint: %HASH%
echo ============================================================
pause
exit /b 0

:find_iscc
set "ISCC="
for %%P in ("%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe") do (
    if not defined ISCC if exist "%%~P" set "ISCC=%%~P"
)
exit /b 0

:fail
echo.
echo ============================================================
echo   Setup failed at step: %STEP%
echo   Please send a screenshot of this whole window.
echo ============================================================
pause
exit /b 1
