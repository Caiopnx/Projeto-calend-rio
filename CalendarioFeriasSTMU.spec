# Execute: python -m PyInstaller --clean --noconfirm CalendarioFeriasSTMU.spec
from PyInstaller.utils.hooks import collect_all
pdf_data, pdf_bins, pdf_hidden = collect_all('pypdfium2')
raw_data, raw_bins, raw_hidden = collect_all('pypdfium2_raw')
a = Analysis(['run.py'], pathex=[], binaries=pdf_bins + raw_bins,
             datas=pdf_data + raw_data + [('app/assets', 'app/assets')],
             hiddenimports=pdf_hidden + raw_hidden,
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['numpy', 'matplotlib', 'pandas', 'pytest'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='CalendarioFeriasSTMU',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False, icon='app/assets/stmu.ico')
