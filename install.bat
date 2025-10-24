@echo off
REM NeoZen Installation Script for Windows
REM This script sets up a virtual environment and installs NeoZen with all dependencies

setlocal enabledelayedexpansion

echo =========================================
echo   NeoZen - Modern Nmap GUI Installer
echo =========================================
echo.

REM Check for Python
echo [1/4] Checking for Python 3...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3 not found.
    echo Please install Python 3.7 or higher from:
    echo   https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Found Python %PYTHON_VERSION%

REM Check for Nmap
echo.
echo [2/4] Checking for Nmap...
nmap --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Nmap not found in PATH.
    echo.
    echo Please download and install Nmap from:
    echo   https://nmap.org/download.html
    echo.
    echo After installation, make sure nmap.exe is in your PATH.
    echo You can continue installation, but NeoZen will not work without Nmap.
    echo.
    choice /C YN /M "Continue anyway"
    if errorlevel 2 exit /b 1
) else (
    for /f "tokens=3" %%i in ('nmap --version 2^>^&1 ^| findstr /C:"Nmap version"') do set NMAP_VERSION=%%i
    echo [OK] Found Nmap !NMAP_VERSION!
)

REM Create virtual environment
echo.
echo [3/4] Creating virtual environment...
if exist venv (
    echo [WARNING] Virtual environment already exists. Removing...
    rmdir /s /q venv
)

python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)
echo [OK] Virtual environment created

REM Activate virtual environment and install
echo.
echo [4/4] Installing NeoZen and dependencies...
call venv\Scripts\activate.bat

REM Upgrade pip
python -m pip install --upgrade pip --quiet

REM Install NeoZen
pip install -e . --quiet

if %errorlevel% neq 0 (
    echo [ERROR] Installation failed.
    pause
    exit /b 1
)

echo [OK] NeoZen installed successfully!

REM Build standalone executable
echo.
echo [EXTRA] Building standalone executable...
pip install -e ".[build]" --quiet

if %errorlevel% equ 0 (
    pyinstaller --clean --noconfirm neozen.spec >nul 2>&1

    REM Move executable to project directory
    if exist "dist\neozen.exe" (
        move /Y dist\neozen.exe neozen.exe >nul
        echo [OK] Standalone executable created: neozen.exe

        REM Clean up build artifacts
        rmdir /S /Q build >nul 2>&1
        rmdir /S /Q dist >nul 2>&1
    ) else (
        echo [WARNING] Standalone executable build failed, but virtual environment installation succeeded.
    )
) else (
    echo [WARNING] Could not install build dependencies, but virtual environment installation succeeded.
)

REM Installation complete
echo.
echo =========================================
echo      Installation Complete!
echo =========================================
echo.
echo To start NeoZen:
echo.
if exist "neozen.exe" (
    echo Option 1 [Recommended]: Run standalone executable
    echo   neozen.exe
    echo.
    echo   Or double-click neozen.exe in File Explorer
    echo.
    echo Option 2: Use virtual environment:
)
echo   venv\Scripts\activate.bat
echo   neozen
echo.
echo Or double-click:
echo   venv\Scripts\neozen.exe
echo.
echo To deactivate the virtual environment later, run:
echo   deactivate
echo.
pause
