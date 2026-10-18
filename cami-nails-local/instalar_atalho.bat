@echo off
setlocal
cd /d "%~dp0"
echo Preparando o atalho da Cami Nails...
if exist .venv\Scripts\python.exe goto dependencias
where py >nul 2>nul
if errorlevel 1 (
 echo Python nao encontrado. Instale o Python 3.11 ou superior e tente novamente.
 goto erro
)
py -m venv .venv
if errorlevel 1 goto erro
:dependencias
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto erro
.venv\Scripts\python.exe -m flask --app run init-db
if errorlevel 1 goto erro
.venv\Scripts\python.exe verificar_admin.py
if errorlevel 11 goto erro
if errorlevel 10 goto admin
if errorlevel 1 goto erro
goto atalho
:admin
echo Primeira instalacao: crie o acesso da administradora.
.venv\Scripts\python.exe -m flask --app run criar-admin
if errorlevel 1 goto erro
:atalho
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0criar_atalho.ps1"
if errorlevel 1 goto erro
echo Pronto! Use o icone Cami Nails na Area de Trabalho.
echo A partir de agora nao e necessario abrir terminal.
pause
exit /b 0
:erro
echo Nao foi possivel concluir. Envie uma foto desta janela para diagnostico.
pause
exit /b 1
