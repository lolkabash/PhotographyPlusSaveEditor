@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON=py -3"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python 3 is required but was not found.
        echo Install it from https://www.python.org/downloads/ and try again.
        pause
        exit /b 1
    )
    set "PYTHON=python"
)

%PYTHON% -c "import sys; raise SystemExit(sys.version_info < (3, 10))"
if errorlevel 1 (
    echo Python 3.10 or newer is required.
    pause
    exit /b 1
)

%PYTHON% -c "import PIL" >nul 2>nul
if errorlevel 1 (
    echo Installing the image library for first use...
    %PYTHON% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Could not install Pillow. Check your internet connection and try again.
        pause
        exit /b 1
    )
)

%PYTHON% run_editor.py
if errorlevel 1 pause