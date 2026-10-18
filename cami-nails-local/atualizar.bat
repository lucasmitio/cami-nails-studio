@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
 echo Ambiente nao encontrado. Siga LEIA-ME.md.
 pause
 exit /b 1
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto erro
.venv\Scripts\python.exe -m flask --app run init-db
if errorlevel 1 goto erro
echo Atualizacao concluida. Abra iniciar.bat.
pause
exit /b 0
:erro
echo Atualizacao interrompida. Envie uma foto do erro.
pause
