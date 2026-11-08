# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller: gera o app com tudo embutido (Windows e Linux).

Windows: dist\\HolyricsBot\\HolyricsBot.exe
Linux:   dist/HolyricsBot/HolyricsBot
"""
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

datas = [
    ("assets", "assets"),
    ("minio-uploader", "minio-uploader"),
]
if os.path.isdir("bin"):
    datas.append(("bin", "bin"))

# pypdfium2 (renderização de PDF) e python-pptx trazem arquivos próprios.
for pacote in ("pypdfium2", "pptx"):
    try:
        datas += collect_data_files(pacote)
    except Exception:
        pass

binaries = []
try:
    binaries += collect_dynamic_libs("pypdfium2")
except Exception:
    pass

if sys.platform.startswith("win"):
    hiddenimports = ["pystray._win32", "pystray._base", "PIL._tkinter_finder"]
    icone = "assets/icon.ico"
else:
    hiddenimports = ["pystray._xorg", "pystray._base", "PIL._tkinter_finder"]
    icone = None

try:
    hiddenimports += collect_submodules("yt_dlp")
except Exception:
    pass

a = Analysis(
    ["holyrics_bot_gui.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HolyricsBot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icone,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="HolyricsBot",
)
