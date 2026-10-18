@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\pythonw.exe (
 call instalar_atalho.bat
 if errorlevel 1 exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "%~dp0abrir_studio.pyw"
