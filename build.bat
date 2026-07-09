@echo off
echo ==============================================
echo Retail Invoice System - Build Script
echo ==============================================

echo Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.12+ from python.org and check "Add python.exe to PATH".
    pause
    exit /b
)

echo Creating Virtual Environment...
python -m venv venv
call venv\Scripts\activate.bat

echo Installing Dependencies...
pip install -r requirements.txt

echo Building Executable with PyInstaller...
pyinstaller --name "RetailInvoice" --windowed --noconfirm --clean ^
    --add-data "assets;assets" ^
    --add-data "ui;ui" ^
    --hidden-import customtkinter ^
    --hidden-import pywin32 ^
    --hidden-import PIL ^
    --hidden-import escpos ^
    main.py

echo ==============================================
echo Build Complete!
echo You can find your compiled .exe in the 'dist/RetailInvoice' folder.
echo ==============================================
pause
