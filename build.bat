@echo off
rem Build PTW_Generator.exe (one file). Run from the project folder: double-click or "build.bat".
rem The exe creates its folders (data, templates, sounds, logs) next to itself on first start.
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Install Python 3.12 or 3.13 from python.org and tick "Add python.exe to PATH".
    pause
    exit /b 1
)

echo === Installing packages ===
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :error

echo === Building ===
python -m PyInstaller --noconfirm --clean --onefile --windowed --name PTW_Generator ^
    --add-data "defaults;defaults" --add-data "templates;templates" --add-data "sounds;sounds" ^
    --add-data "icons;icons" --icon icons\ptw.ico ^
    --hidden-import babel.numbers main.py
if errorlevel 1 goto :error

echo.
echo Done: dist\PTW_Generator.exe
echo Copy only this file to the ship computer (or a network folder) and start it.
pause
exit /b 0

:error
echo.
echo BUILD FAILED - see the messages above.
pause
exit /b 1
