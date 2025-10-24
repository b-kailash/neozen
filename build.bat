@echo off
REM Build script for NeoZen on Windows
REM Creates a standalone executable in the project directory

setlocal enabledelayedexpansion

echo ======================================
echo NeoZen Build Script (Windows)
echo ======================================
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Virtual environment not found. Creating one...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment
        exit /b 1
    )
    echo Virtual environment created
)

REM Activate virtual environment
echo Installing dependencies...
call venv\Scripts\activate.bat

REM Upgrade pip and install dependencies
python -m pip install --upgrade pip >nul 2>&1
pip install -e ".[build]" >nul 2>&1
echo Dependencies installed
echo.

REM Build with PyInstaller
echo Building executable with PyInstaller...
pyinstaller --clean --noconfirm neozen.spec
if errorlevel 1 (
    echo Build failed
    exit /b 1
)

REM Move executable to project directory
echo Moving executable to project directory...
if exist "dist\neozen.exe" (
    move /Y dist\neozen.exe neozen.exe >nul
    echo Executable created: neozen.exe
) else (
    echo Build failed: executable not found in dist/
    exit /b 1
)

REM Clean up build artifacts
echo Cleaning up build artifacts...
rmdir /S /Q build >nul 2>&1
rmdir /S /Q dist >nul 2>&1
del *.spec~ >nul 2>&1
echo Cleanup complete
echo.

REM Summary
echo ======================================
echo Build successful!
echo ======================================
echo.
echo Run the application with:
echo   neozen.exe
echo.
echo Or double-click neozen.exe in File Explorer
echo.
echo To make it available from anywhere, add the project directory to your PATH
echo.

endlocal
