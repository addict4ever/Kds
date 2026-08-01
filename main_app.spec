# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['flask', 'pymodbus.client.sync', 'pymodbus', 'qrcode', 'pyotp', 'hashlib', 'requests', 'jinja2', 'werkzeug', 'serial.tools.list_ports', 'uuid', 'socket', 'tkcalendar', 'psutil', 'pygame', 'matplotlib', 'matplotlib.backends.backend_tkagg', 'numpy', 'PIL', 'PIL._tkinter_finder', 'uuid', 'tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.filedialog', 'tkinter.simpledialog', 'tkinter.colorchooser', 'tkinter.scrolledtext', 'serial', 'sqlite3', 'json', 'logging', 'datetime', 'math', 'hashlib', 're', 'threading', 'platform', 'winsound', 'shutil', 'subprocess']
hiddenimports += collect_submodules('flask')


a = Analysis(
    ['main_app.py'],
    pathex=[],
    binaries=[],
    datas=[('templates', 'templates'), ('static', 'static'), ('sound', 'sound'), ('postit_widget.py', '.'), ('db_manager.py', '.'), ('db_maindish.py', '.'), ('db_maindish_gui.py', '.'), ('kds_constants.py', '.'), ('kds_gui.py', '.'), ('serial_reader.py', '.'), ('keyboardModifier.py', '.'), ('timer_widget.py', '.'), ('consultation.py', '.'), ('cmd_tool.py', '.'), ('edit_config.py', '.'), ('loginpass.py', '.'), ('kds_total_widget.py', '.'), ('DBKonstantesManager.py', '.'), ('kds_trash_window.py', '.'), ('keyboard.py', '.'), ('popit.py', '.'), ('log_view.py', '.'), ('config_menu.py', '.'), ('utils.py', '.'), ('web_access.py', '.'), ('animate_pack.py', '.'), ('salade_game.py', '.'), ('testprint.py', '.'), ('floating_note.py', '.'), ('test_print_net.py', '.'), ('web_access.py', '.'), ('thermometer_widget.py', '.'), ('pyarmor_runtime_000000', 'pyarmor_runtime_000000')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['pizzeria_kds.ico'],
)
