$ErrorActionPreference = 'Stop'
$studioRoot = $PSScriptRoot
$studioPython = Join-Path $studioRoot '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $studioPython)) { throw 'Ambiente Python nao encontrado.' }
$desktopPath = [Environment]::GetFolderPath('Desktop')
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut((Join-Path $desktopPath 'Cami Nails.lnk'))
$link.TargetPath = $studioPython
$link.Arguments = '"' + (Join-Path $studioRoot 'abrir_studio.pyw') + '"'
$link.WorkingDirectory = $studioRoot
$link.IconLocation = (Join-Path $studioRoot 'app\static\cami-nails.ico') + ',0'
$link.Description = 'Abrir o sistema do Studio Cami Nails'
$link.Save()
Write-Host 'Atalho Cami Nails criado na Area de Trabalho.'
