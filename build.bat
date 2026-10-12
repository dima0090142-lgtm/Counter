@echo off
rem Build PTW_Generator.exe (Windows). Run from the project folder: double-click or "build.bat".
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Install Python 3.10+ from python.org and tick "Add python.exe to PATH".
    pause
    exit /b 1
)

echo === Installing packages ===
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :error

echo === Running tests ===
python -m pip install pytest
python -m pytest -q tests
if errorlevel 1 goto :error

echo === Building ===
python -m PyInstaller --noconfirm --clean --windowed --name PTW_Generator ^
    --add-data "defaults;defaults" --add-data "templates;templates" --add-data "sounds;sounds" ^
    --add-data "icons;icons" --icon icons\ptw.ico ^
    --hidden-import babel.numbers main.py
if errorlevel 1 goto :error

echo.
echo Done: dist\PTW_Generator\PTW_Generator.exe
echo Copy the whole folder dist\PTW_Generator to the ship computer.
pause
exit /b 0

:error
echo.
echo BUILD FAILED - see the messages above.
pause
exit /b 1
