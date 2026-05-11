@echo off
echo ============================================
echo  Keep Awake - Setup
echo ============================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python not found. Please install it first:
    echo     1. Go to https://www.python.org/downloads/
    echo     2. Download the latest version
    echo     3. During install, check "Add Python to PATH"
    echo     4. Re-run this setup after installing.
    pause
    exit /b 1
)

echo [OK] Python found.
echo.
echo [*] Installing required libraries...
pip install pyautogui pystray pillow --quiet

if %errorlevel% neq 0 (
    echo [!] Failed to install libraries. Check your internet connection.
    pause
    exit /b 1
)

echo [OK] Libraries installed.
echo.
echo ============================================
echo  Setup complete! Run "start.bat" to launch.
echo ============================================
pause
