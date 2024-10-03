@echo off
:: Set window label
FOR /F "tokens=* USEBACKQ" %%F IN (`py --version`) DO (SET pyversion=%%F)
title archive XKCD - %pyversion%

:: Change cwd to script dir.
cd %~dp0

echo Setting up...
:: Run dependency install without displaying to console before script:
.\install_dependencies.bat >nul 2>&1 & echo Done. & py -m downloadXKCD & PAUSE