# Quick Start: Building v2.1.1 for Distribution

## For Non-Technical Users (End Users)

**Just double-click the .exe file!**

1. Download `QTR_Pairing_Process_v2.1.1.exe`
2. Save it anywhere (Desktop, Documents, etc.)
3. Double-click to run
4. If Windows SmartScreen appears, click "More info" → "Run anyway"

**That's it!** No installation, no Python, no setup required.

---

## For Developers/Release Managers

### Build the Standalone .exe

```powershell
# Navigate to project directory
cd "C:\Users\Daniel.Raven\OneDrive - Vertex, Inc\Documents\OSeries\Elite Services\Python\QTR_pairing_process"

# Build v2.1.1
.\scripts\build_release.ps1 -Version 2.1.1
```

**Output location**: `release/v2.1.1/QTR_Pairing_Process_v2.1.1.exe`

### What Changed for v2.1.1

✅ **New Files Created**:
- `QTR_Pairing_Process.spec` - PyInstaller configuration for proper bundling
- `file_version_info.txt` - Windows version metadata
- `RELEASE_READINESS_v2.1.1.md` - Complete release audit report

✅ **Updated Files**:
- `scripts/build_release.ps1` - Now uses .spec file for better dependency handling

### Why These Changes Matter

**Before**: Basic PyInstaller build that might miss dependencies
**After**: Explicitly bundles all tkinter, openpyxl, and runtime requirements

**Result**: The .exe will work on **any Windows PC** even if:
- They don't have Python installed
- They've never installed openpyxl
- Their PATH is not configured
- They have no development tools

### Testing on a Clean Machine

**Critical**: Test on a PC **without Python** before distributing:

1. Find a Windows PC that has never had Python
2. Copy only the .exe file to that PC
3. Double-click it
4. Test these workflows:
   - Create a new team
   - Import an Excel file
   - Generate pairings
   - Export to CSV
   - Save and reload

If all work → ✅ Ready to distribute!

### Build Flags Explained

The new `.spec` file includes:

```python
console=False  # No black console window (clean GUI launch)
onefile=True   # Everything in one .exe (user-friendly)
hiddenimports=[
    'tkinter.ttk',     # GUI components
    'openpyxl',        # Excel support
    # ... all dependencies
]
```

This ensures the .exe is truly standalone.

---

## Troubleshooting

### "Build failed" during PyInstaller

**Solution**: Make sure PyInstaller is installed:
```powershell
.venv\Scripts\pip.exe install pyinstaller==6.19.0
```

### ".exe doesn't launch on test machine"

**Check**:
1. Is it Windows 10/11? (required)
2. Did Windows Defender block it? (check quarantine)
3. Did SmartScreen appear? (click "Run anyway")
4. Check Windows Event Viewer for error details

### ".exe is missing functionality"

**Check**: The `.spec` file includes all needed imports. If something is missing, add to `hiddenimports` list.

---

## Version Numbering

For future releases, update version in **3 places**:

1. `QTR_Pairing_Process.spec` - Line 59: `name='QTR_Pairing_Process_v2.1.1'`
2. `file_version_info.txt` - Lines 7-8: `filevers=(2, 1, 1, 0)` and `prodvers=(2, 1, 1, 0)`
3. Build command: `.\scripts\build_release.ps1 -Version 2.1.1`

---

## Distribution Checklist

Before sending to users:

- [ ] Built using the .spec file
- [ ] Tested on clean Windows PC (no Python)
- [ ] Verified file size (20-40 MB expected)
- [ ] Generated SHA256 checksum (automatic)
- [ ] Prepared user guide for SmartScreen bypass
- [ ] Uploaded to secure distribution location
- [ ] Notified users of new version

---

## Support for Non-Tech-Savvy Users

**What to tell users**:

> "Here's the QTR pairing tool. Just save the .exe file anywhere on your computer and double-click it to run. If Windows shows a security warning, click 'More info' and then 'Run anyway'. That's because the app isn't signed with an expensive certificate, but it's safe. The tool will create a few files next to where you save it (for your data and settings)."

**Common questions**:

*Q: Do I need to install Python?*
A: Nope! Everything is built into the .exe.

*Q: Can I put it on my Desktop?*
A: Yes, anywhere you want!

*Q: Why does Windows say it's unsafe?*
A: It's just Windows being cautious about unsigned apps. Click "Run anyway" and you're good.

*Q: Where is my data saved?*
A: In the same folder as the .exe, in files that start with "KLIK_KLAK" and end with ".json" or ".db".

---

## Need Help?

Check the full release audit: `RELEASE_READINESS_v2.1.1.md`
