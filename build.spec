# build.spec - packs ClearTrace into ONE file with PyInstaller.
#   pip install -r requirements.txt pyinstaller
#   pyinstaller build.spec --noconfirm
# Windows -> dist/ClearTrace.exe     Mac -> dist/ClearTrace.app
import sys

from PyInstaller.utils.hooks import collect_data_files

datas = [("ui", "ui")]
datas += collect_data_files("docx")        # Word reader templates
datas += collect_data_files("webview")     # pywebview's JS bridge

# Big libraries ClearTrace never uses: leaving them out keeps the file small
excludes = ["tkinter", "numpy", "pandas", "matplotlib", "PIL", "scipy", "IPython",
            "pytest", "streamlit", "pdfplumber", "reportlab", "fastapi", "uvicorn"]

a = Analysis(
    ["main.py"],
    datas=datas,
    hiddenimports=["send2trash"],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="ClearTrace",
    console=False,          # no black terminal window
    upx=False,              # UPX often triggers antivirus false alarms
    debug=False,
    strip=False,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="ClearTrace.app",
        bundle_identifier="com.cleartrace.app",
        info_plist={"NSHighResolutionCapable": True},
    )
