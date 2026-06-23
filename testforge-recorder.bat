@echo off
REM TestForge Recorder GUI — Windows launcher
REM Coloque este arquivo junto com activate.bat ou na pasta do TestForge
REM Crie um atalho deste .bat na área de trabalho para usar como ícone

cd /d "%~dp0"

REM Ativa o venv se existir
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Inicia a interface gráfica (sem janela de terminal)
pythonw -m testforge.gui.recorder_launcher

REM Fallback: se pythonw não funcionar, tenta python normal
if errorlevel 1 (
    python -m testforge.gui.recorder_launcher
)
