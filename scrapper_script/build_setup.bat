@echo off
echo ========================================
echo Google Maps Scraper GUI - Build Setup
echo ========================================
echo.

echo Installing required packages...
python -m pip install --upgrade pip
python -m pip install pyinstaller
python -m pip install -r requirements_gui.txt

echo.
echo Building GUI executable...
python build_gui_exe.py

echo.
echo Build process completed!
echo Check the 'dist' folder for your GUI executable.
pause