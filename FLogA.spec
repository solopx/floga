from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

babel_datas = collect_data_files('babel')

a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=[],
    datas=babel_datas,
    hiddenimports=[
        'matplotlib.backends.backend_tkagg',
        'matplotlib.backends.backend_agg',
        'matplotlib._afm',
        'matplotlib._cm',
        'matplotlib._path',
        'babel.numbers',
        'babel.dates',
        'babel.core',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', '_pytest', 'py', 'pluggy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FLogA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)
