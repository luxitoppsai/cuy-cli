@echo off
REM Lanza cuy-cli en Windows. La logica vive en cuy.py (multiplataforma).
REM chcp 65001 pone la consola en UTF-8: sin eso los bloques del logo se ven como basura.
chcp 65001 >nul 2>&1
python "%~dp0cuy.py" %*
