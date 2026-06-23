# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all
import sys

sys.setrecursionlimit(10000)

import glob
datas = []
binaries = []
hiddenimports = []

for dll in glob.glob(r"C:\Windows\System32\msvcp140*.dll") + glob.glob(r"C:\Windows\System32\vcruntime140*.dll") + glob.glob(r"C:\Windows\System32\vcomp140*.dll"):
    binaries.append((dll, "."))


essential_packages = [
    "lspopt",
    "mne",
    "yasa",
    "sleepeegpy",
    "sv_ttk",
    "specparam",
    "googleapiclient",
    "google.oauth2",
    "google",
    "tensorflow",
    "tf_keras"
]

for pkg in essential_packages:
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

hiddenimports += [
    "docx",
    "docx2pdf",
    "pypdf",
    "fitz",
    "defusedxml",
    "lightgbm",
    "sklearn",
    "antropy",
    "seaborn",
    "numpy",
    "scipy",
    "pandas",
    "matplotlib",
    "PIL",
    "pyedflib",
    "pyedflib.highlevel",
    "scipy.signal",
    "pipeline",
    "caisr_bridge",
    "gdrive_sync",
    "bidi",
    "patient_report",
    "config_colors",
    "tensorflow",
    "tf_keras"
]

hiddenimports = sorted(set(hiddenimports))

datas += [
    ("RBDtector", "RBDtector"), 
    ("ynir.ico", "."),          
    ("splash.mp4", "."),
    ("gdrive_credentials.json", "."),
    ("logo_up.png", "."),
    ("logo_down.png", "."),
    ("CAISR-App-main/stage", "CAISR-App-main/stage")
]

a = Analysis(
    ["app.py"],
    pathex=[".", "CAISR-App-main", "CAISR-App-main/limb", "CAISR-App-main/stage", "CAISR-App-main/stage/graphsleepnet"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["rthook_tf_first.py"],
    excludes=["pandas.tests", "scipy.tests", "numpy.tests"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SleepApp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['ynir.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SleepApp",
)
