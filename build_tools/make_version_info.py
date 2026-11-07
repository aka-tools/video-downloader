# Copyright (c) 2026 AKA. All rights reserved.
"""Build helper: writes the Windows version resource (Properties > Details) from APP_VERSION
and prints the version so Setup.bat can pass it to the installer compiler."""
import os
import re
import sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(root, "app", "video_downloader.py"), encoding="utf-8").read()
out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "_build", "version_info.txt")
label = re.search(r'^APP_LABEL = "([^"]+)"', src, re.M).group(1)
ver = re.search(r'^APP_VERSION = "(\d+)\.(\d+)\.(\d+)"', src, re.M)
author = re.search(r'^APP_AUTHOR = "([^"]+)"', src, re.M).group(1)
if not ver:
    sys.exit("APP_VERSION not found")
a, b, c = ver.groups()
text = f'''VSVersionInfo(
  ffi=FixedFileInfo(filevers=({a}, {b}, {c}, 0), prodvers=({a}, {b}, {c}, 0),
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', '{author}'),
      StringStruct('FileDescription', 'Video Downloader {label}'),
      StringStruct('FileVersion', '{a}.{b}.{c}'),
      StringStruct('InternalName', 'VideoDownloader'),
      StringStruct('LegalCopyright', 'Copyright (c) 2026 {author}. All rights reserved.'),
      StringStruct('OriginalFilename', 'VideoDownloader.exe'),
      StringStruct('ProductName', 'Video Downloader'),
      StringStruct('ProductVersion', '{label}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
'''
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    f.write(text)
print(f"{a}.{b}.{c} {label}")
