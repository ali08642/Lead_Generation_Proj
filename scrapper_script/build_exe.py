#!/usr/bin/env python3
"""
Build script to create a single executable for Google Maps Scraper
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_requirements():
    """Install required packages for building"""
    print("📦 Installing build requirements...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements_build.txt"], check=True)

def create_spec_file():
    """Create PyInstaller spec file"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('scraper_config.json', '.'),
        ('database_schema.sql', '.'),
        ('database_schema_updated.sql', '.'),
    ],
    hiddenimports=[
        'playwright',
        'playwright.sync_api',
        'playwright.async_api',
        'flask',
        'flask.json',
        'supabase',
        'phonenumbers',
        'python-dotenv',
        'requests',
        'httpx',
        'httpcore',
        'werkzeug',
        'sqlite3',
        'asyncio',
        'aiohttp',
        'websockets',
        'psutil',
        'pydantic',
        'typing_extensions',
        'packaging',
        'certifi',
        'charset_normalizer',
        'idna',
        'urllib3',
        'click',
        'itsdangerous',
        'jinja2',
        'markupsafe',
        'blinker',
        'postgrest',
        'gotrue',
        'realtime',
        'storage3',
        'functions',
        'supabase.lib.client_options',
        'supabase.lib.client_options.client_options',
        'supabase.lib.client_options.client_options.ClientOptions',
        'supabase.lib.client_options.client_options.ClientOptions.__init__',
        'supabase.lib.client_options.client_options.ClientOptions.__new__',
        'supabase.lib.client_options.client_options.ClientOptions.__call__',
        'supabase.lib.client_options.client_options.ClientOptions.__getattr__',
        'supabase.lib.client_options.client_options.ClientOptions.__setattr__',
        'supabase.lib.client_options.client_options.ClientOptions.__delattr__',
        'supabase.lib.client_options.client_options.ClientOptions.__getattribute__',
        'supabase.lib.client_options.client_options.ClientOptions.__getitem__',
        'supabase.lib.client_options.client_options.ClientOptions.__setitem__',
        'supabase.lib.client_options.client_options.ClientOptions.__delitem__',
        'supabase.lib.client_options.client_options.ClientOptions.__iter__',
        'supabase.lib.client_options.client_options.ClientOptions.__next__',
        'supabase.lib.client_options.client_options.ClientOptions.__contains__',
        'supabase.lib.client_options.client_options.ClientOptions.__len__',
        'supabase.lib.client_options.client_options.ClientOptions.__bool__',
        'supabase.lib.client_options.client_options.ClientOptions.__hash__',
        'supabase.lib.client_options.client_options.ClientOptions.__str__',
        'supabase.lib.client_options.client_options.ClientOptions.__repr__',
        'supabase.lib.client_options.client_options.ClientOptions.__format__',
        'supabase.lib.client_options.client_options.ClientOptions.__lt__',
        'supabase.lib.client_options.client_options.ClientOptions.__le__',
        'supabase.lib.client_options.client_options.ClientOptions.__eq__',
        'supabase.lib.client_options.client_options.ClientOptions.__ne__',
        'supabase.lib.client_options.client_options.ClientOptions.__gt__',
        'supabase.lib.client_options.client_options.ClientOptions.__ge__',
        'supabase.lib.client_options.client_options.ClientOptions.__add__',
        'supabase.lib.client_options.client_options.ClientOptions.__sub__',
        'supabase.lib.client_options.client_options.ClientOptions.__mul__',
        'supabase.lib.client_options.client_options.ClientOptions.__truediv__',
        'supabase.lib.client_options.client_options.ClientOptions.__floordiv__',
        'supabase.lib.client_options.client_options.ClientOptions.__mod__',
        'supabase.lib.client_options.client_options.ClientOptions.__divmod__',
        'supabase.lib.client_options.client_options.ClientOptions.__pow__',
        'supabase.lib.client_options.client_options.ClientOptions.__lshift__',
        'supabase.lib.client_options.client_options.ClientOptions.__rshift__',
        'supabase.lib.client_options.client_options.ClientOptions.__and__',
        'supabase.lib.client_options.client_options.ClientOptions.__xor__',
        'supabase.lib.client_options.client_options.ClientOptions.__or__',
        'supabase.lib.client_options.client_options.ClientOptions.__radd__',
        'supabase.lib.client_options.client_options.ClientOptions.__rsub__',
        'supabase.lib.client_options.client_options.ClientOptions.__rmul__',
        'supabase.lib.client_options.client_options.ClientOptions.__rtruediv__',
        'supabase.lib.client_options.client_options.ClientOptions.__rfloordiv__',
        'supabase.lib.client_options.client_options.ClientOptions.__rmod__',
        'supabase.lib.client_options.client_options.ClientOptions.__rdivmod__',
        'supabase.lib.client_options.client_options.ClientOptions.__rpow__',
        'supabase.lib.client_options.client_options.ClientOptions.__rlshift__',
        'supabase.lib.client_options.client_options.ClientOptions.__rrshift__',
        'supabase.lib.client_options.client_options.ClientOptions.__rand__',
        'supabase.lib.client_options.client_options.ClientOptions.__rxor__',
        'supabase.lib.client_options.client_options.ClientOptions.__ror__',
        'supabase.lib.client_options.client_options.ClientOptions.__iadd__',
        'supabase.lib.client_options.client_options.ClientOptions.__isub__',
        'supabase.lib.client_options.client_options.ClientOptions.__imul__',
        'supabase.lib.client_options.client_options.ClientOptions.__itruediv__',
        'supabase.lib.client_options.client_options.ClientOptions.__ifloordiv__',
        'supabase.lib.client_options.client_options.ClientOptions.__imod__',
        'supabase.lib.client_options.client_options.ClientOptions.__ipow__',
        'supabase.lib.client_options.client_options.ClientOptions.__ilshift__',
        'supabase.lib.client_options.client_options.ClientOptions.__irshift__',
        'supabase.lib.client_options.client_options.ClientOptions.__iand__',
        'supabase.lib.client_options.client_options.ClientOptions.__ixor__',
        'supabase.lib.client_options.client_options.ClientOptions.__ior__',
        'supabase.lib.client_options.client_options.ClientOptions.__neg__',
        'supabase.lib.client_options.client_options.ClientOptions.__pos__',
        'supabase.lib.client_options.client_options.ClientOptions.__abs__',
        'supabase.lib.client_options.client_options.ClientOptions.__invert__',
        'supabase.lib.client_options.client_options.ClientOptions.__complex__',
        'supabase.lib.client_options.client_options.ClientOptions.__int__',
        'supabase.lib.client_options.client_options.ClientOptions.__float__',
        'supabase.lib.client_options.client_options.ClientOptions.__round__',
        'supabase.lib.client_options.client_options.ClientOptions.__trunc__',
        'supabase.lib.client_options.client_options.ClientOptions.__floor__',
        'supabase.lib.client_options.client_options.ClientOptions.__ceil__',
        'supabase.lib.client_options.client_options.ClientOptions.__enter__',
        'supabase.lib.client_options.client_options.ClientOptions.__exit__',
        'supabase.lib.client_options.client_options.ClientOptions.__await__',
        'supabase.lib.client_options.client_options.ClientOptions.__aiter__',
        'supabase.lib.client_options.client_options.ClientOptions.__anext__',
        'supabase.lib.client_options.client_options.ClientOptions.__aenter__',
        'supabase.lib.client_options.client_options.ClientOptions.__aexit__',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='GoogleMapsScraper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''
    
    with open('GoogleMapsScraper.spec', 'w') as f:
        f.write(spec_content)
    print("📄 Created PyInstaller spec file")

def build_executable():
    """Build the executable"""
    print("🔨 Building executable...")
    
    # Clean previous builds
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    # Build with PyInstaller
    result = subprocess.run([
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--onefile',
        '--console',
        '--name=GoogleMapsScraper',
        'main.py'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print("❌ Build failed!")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        return False
    
    print("✅ Build completed successfully!")
    return True

def create_run_script():
    """Create a simple run script for the executable"""
    run_script = '''@echo off
echo Starting Google Maps Scraper...
echo.
echo The server will be available at: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.
GoogleMapsScraper.exe
pause
'''
    
    with open('run_scraper.bat', 'w') as f:
        f.write(run_script)
    print("📝 Created run script: run_scraper.bat")

def main():
    """Main build process"""
    print("🚀 Starting Google Maps Scraper Build Process")
    print("=" * 50)
    
    try:
        # Install requirements
        install_requirements()
        
        # Create spec file
        create_spec_file()
        
        # Build executable
        if build_executable():
            # Create run script
            create_run_script()
            
            print("\n🎉 Build completed successfully!")
            print("📁 Executable location: dist/GoogleMapsScraper.exe")
            print("📁 Run script: run_scraper.bat")
            print("\nTo run the scraper:")
            print("1. Double-click run_scraper.bat")
            print("2. Or run: dist/GoogleMapsScraper.exe")
            print("\nThe server will start on http://localhost:5000")
    else:
            print("❌ Build failed!")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Build process failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()