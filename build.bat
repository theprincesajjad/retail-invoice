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

echo Installing PyInstaller...
pip install pyinstaller

echo Building single-file Executable with PyInstaller...
pyinstaller --name "RetailInvoice" --onefile --windowed --noconfirm --clean ^
    --add-data "assets;assets" ^
    --add-data "VERSION;." ^
    --add-data "CHANGELOG.md;." ^
    --collect-all customtkinter ^
    --hidden-import customtkinter ^
    --hidden-import pywin32 ^
    --hidden-import PIL ^
    --hidden-import escpos ^
    --hidden-import win32print ^
    --hidden-import win32api ^
    --hidden-import reportlab ^
    --hidden-import reportlab.pdfgen.canvas ^
    --hidden-import openpyxl ^
    main.py

echo ==============================================
echo Build Complete!
echo You can find your compiled .exe in the 'dist' folder:
echo   dist\RetailInvoice.exe
echo ==============================================
pause
