@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"
title TestForge - Instalador 1 clique

set "INSTALLER_DIR=%~dp0"
if "%INSTALLER_DIR:~-1%"=="\" set "INSTALLER_DIR=%INSTALLER_DIR:~0,-1%"

set "LOG_FILE=%CD%\testforge_install.log"
set "FAIL=0"
set "PY_CMD="
set "PY_KIND="
set "GIT_OK=0"
set "FAIL_REASON="
set "START_DIR=%CD%"
set "REPO_URL=https://alm.ceaus.df.caixa/CEGTI/AUTOMATA-PRIMUS/_git/AUTOMATA-PRIMUS"
set "TARGET_BRANCH=update-gravador"
set "REPO_DIR_NAME=AUTOMATA-PRIMUS"
set "CLONE_BASE=%USERPROFILE%\AP"
set "CLONE_BASE_FALLBACK=C:\AP"
set "DEFAULT_CLONE_ROOT=%CLONE_BASE%\%REPO_DIR_NAME%"
set "CAIXA_INDEX_OK=0"
set "INSTALL_OK=0"
set "INSTALL_EXTRAS=.[dev]"
set "REPO_ROOT_FINAL="
set "SHORTCUT_OK=0"
set "SHORTCUT_NAME=TestForge Recorder (CAIXA).lnk"

set "CAIXA_PIP_INDEX=http://binario.caixa:8081/repository/pypi-repo/simple/"
set "CAIXA_PIP_TRUSTED_HOST=binario.caixa"
set "PUBLIC_PYPI_INDEX=https://pypi.org/simple"
set "WHEELHOUSE=%CD%\wheelhouse"

cls
echo ========================================================== > "%LOG_FILE%"
echo TestForge - Instalador 1 clique >> "%LOG_FILE%"
echo Inicio: %DATE% %TIME% >> "%LOG_FILE%"
echo Pasta: %CD% >> "%LOG_FILE%"
echo ========================================================== >> "%LOG_FILE%"

echo ==========================================================
echo  TestForge - Instalador Windows 1 clique
echo ==========================================================
echo.
echo Este instalador foi preparado para funcionar em dois cenarios:
echo.
echo  1. Ambiente CAIXA
echo     - tenta usar automaticamente o repositorio interno binario.caixa
echo.
echo  2. Fabrica de software
echo     - se o repositorio CAIXA nao estiver acessivel, tenta alternativas
echo       automaticamente, sem exigir parametro de linha de comando.
echo.
echo Nenhum comando precisa ser digitado pelo usuario.
echo.
echo Um log sera salvo em:
echo %LOG_FILE%
echo.
echo Iniciando validacoes...
echo.

call :log "Validando Git"
where git >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Git nao encontrado no PATH.
    echo.
    echo Este instalador precisa do Git para clonar o repositorio e selecionar a branch %TARGET_BRANCH%.
    echo [ERRO] Git nao encontrado no PATH. >> "%LOG_FILE%"
    goto :fatal
) else (
    for /f "delims=" %%G in ('git --version') do set "GIT_VER=%%G"
    set "GIT_OK=1"
    echo [OK] !GIT_VER!
    echo [OK] !GIT_VER! >> "%LOG_FILE%"
)
echo.

call :log "Preparando repositorio - clone/checkout da branch"
call :prepare_repository
if errorlevel 1 (
    if not defined FAIL_REASON set "FAIL_REASON=Falha na etapa de preparo do repositorio."
    goto :fatal
)
set "REPO_ROOT_FINAL=%CD%"
echo [OK] Pasta final do repositorio: %REPO_ROOT_FINAL%
echo [OK] Pasta final do repositorio: %REPO_ROOT_FINAL% >> "%LOG_FILE%"
echo.

call :log "Validando Python"
where py >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py -3"
    set "PY_KIND=py"
)

if not defined PY_CMD (
    where python >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=python"
        set "PY_KIND=python"
    )
)

if not defined PY_CMD (
    echo [ERRO] Python nao encontrado no PATH.
    echo.
    echo No ambiente CAIXA, solicite/instale Python 3.10+ pelo catalogo interno autorizado.
    echo Na fabrica, instale Python 3.10+ e habilite Add Python to PATH.
    echo [ERRO] Python nao encontrado no PATH. >> "%LOG_FILE%"
    goto :fatal
)

for /f "delims=" %%V in ('%PY_CMD% -c "import sys; print(str(sys.version_info[0])+'.'+str(sys.version_info[1]))"') do set "PY_VER=%%V"
for /f "tokens=1,2 delims=." %%A in ("%PY_VER%") do (
    set "PY_MAJOR=%%A"
    set "PY_MINOR=%%B"
)

echo [OK] Python %PY_VER% detectado via %PY_KIND%.
echo [OK] Python %PY_VER% detectado via %PY_KIND%. >> "%LOG_FILE%"

if %PY_MAJOR% LSS 3 (
    echo [ERRO] Python 3.10+ obrigatorio.
    echo [ERRO] Python 3.10+ obrigatorio. >> "%LOG_FILE%"
    goto :fatal
)
if %PY_MAJOR% EQU 3 if %PY_MINOR% LSS 10 (
    echo [ERRO] Python 3.10+ obrigatorio. Versao atual: %PY_VER%
    echo [ERRO] Python 3.10+ obrigatorio. Versao atual: %PY_VER% >> "%LOG_FILE%"
    goto :fatal
)
echo.

call :log "Criando ou reutilizando ambiente virtual"
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Criando ambiente virtual .venv ...
    echo [INFO] Criando ambiente virtual .venv ... >> "%LOG_FILE%"
    %PY_CMD% -m venv .venv >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        echo [ERRO] Falha ao criar .venv.
        goto :fatal
    )
) else (
    echo [OK] Ambiente virtual .venv ja existe.
    echo [OK] Ambiente virtual .venv ja existe. >> "%LOG_FILE%"
)

set "VENV_PY=.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo [ERRO] Nao foi encontrado %VENV_PY%.
    echo [ERRO] Nao foi encontrado %VENV_PY%. >> "%LOG_FILE%"
    goto :fatal
)
echo.

call :log "Preparando configuracao local do pip"
if not exist "%CD%\.venv\pip.ini" (
    > "%CD%\.venv\pip.ini" echo [global]
    >> "%CD%\.venv\pip.ini" echo index-url = %CAIXA_PIP_INDEX%
    >> "%CD%\.venv\pip.ini" echo trusted-host = %CAIXA_PIP_TRUSTED_HOST%
    echo [OK] pip.ini local criado em .venv\pip.ini
    echo [OK] pip.ini local criado em .venv\pip.ini >> "%LOG_FILE%"
) else (
    echo [OK] pip.ini local ja existe em .venv\pip.ini
    echo [OK] pip.ini local ja existe em .venv\pip.ini >> "%LOG_FILE%"
)

echo.
echo [INFO] Detectando automaticamente o melhor modo de instalacao...
echo [INFO] Detectando automaticamente o melhor modo de instalacao... >> "%LOG_FILE%"

set "PIP_CAIXA_ARGS=--index-url %CAIXA_PIP_INDEX% --trusted-host %CAIXA_PIP_TRUSTED_HOST%"
set "PIP_PUBLIC_ARGS=--isolated --index-url %PUBLIC_PYPI_INDEX%"
if defined CAIXA_PIP_CERT set "PIP_CAIXA_ARGS=%PIP_CAIXA_ARGS% --cert %CAIXA_PIP_CERT%"
if defined CAIXA_PIP_CERT set "PIP_PUBLIC_ARGS=%PIP_PUBLIC_ARGS% --cert %CAIXA_PIP_CERT%"

if exist "%WHEELHOUSE%\*.whl" (
    echo [OK] Pasta wheelhouse encontrada. Ela sera usada como alternativa local.
    echo [OK] Pasta wheelhouse encontrada. >> "%LOG_FILE%"
) else (
    echo [INFO] Pasta wheelhouse nao encontrada. Instalacao seguira por repositorio.
    echo [INFO] Pasta wheelhouse nao encontrada. >> "%LOG_FILE%"
)

echo.
echo [1/3] Testando repositorio interno CAIXA...
echo [1/3] Testando repositorio interno CAIXA... >> "%LOG_FILE%"
"%VENV_PY%" -m pip index versions pip %PIP_CAIXA_ARGS% >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [WARN] Repositorio CAIXA nao acessivel neste ambiente.
    echo [WARN] Repositorio CAIXA nao acessivel neste ambiente. >> "%LOG_FILE%"
) else (
    set "CAIXA_INDEX_OK=1"
    echo [OK] Repositorio CAIXA acessivel.
    echo [OK] Repositorio CAIXA acessivel. >> "%LOG_FILE%"
)

echo.
if "%CAIXA_INDEX_OK%"=="1" (
    echo [2/3] Instalando pelo repositorio interno CAIXA...
    echo [2/3] Instalando pelo repositorio interno CAIXA... >> "%LOG_FILE%"
    call :install_from_caixa
    if not errorlevel 1 set "INSTALL_OK=1"
)

if not "%INSTALL_OK%"=="1" if exist "%WHEELHOUSE%\*.whl" (
    echo.
    echo [2/3] Tentando instalacao local pela pasta wheelhouse...
    echo [2/3] Tentando instalacao local pela pasta wheelhouse... >> "%LOG_FILE%"
    call :install_from_wheelhouse
    if not errorlevel 1 set "INSTALL_OK=1"
)

if not "%INSTALL_OK%"=="1" (
    echo.
    echo [3/3] Tentando fallback para PyPI publico...
    echo       Este caminho atende a fabrica quando ela estiver fora da rede CAIXA.
    echo [3/3] Tentando fallback para PyPI publico... >> "%LOG_FILE%"
    call :install_from_public_pypi
    if not errorlevel 1 set "INSTALL_OK=1"
)

if "%INSTALL_OK%"=="1" goto :success

echo [ERRO] Todas as tentativas de instalacao falharam.
echo [ERRO] Todas as tentativas de instalacao falharam. >> "%LOG_FILE%"
goto :fatal

:install_from_caixa
"%VENV_PY%" -m ensurepip --upgrade >> "%LOG_FILE%" 2>&1
"%VENV_PY%" -m pip install --upgrade pip setuptools wheel %PIP_CAIXA_ARGS% >> "%LOG_FILE%" 2>&1
if errorlevel 1 exit /b 1
"%VENV_PY%" -m pip install -e "%INSTALL_EXTRAS%" %PIP_CAIXA_ARGS% >> "%LOG_FILE%" 2>&1
exit /b %ERRORLEVEL%

:prepare_repository
set "REPO_ROOT="

if exist "%START_DIR%\pyproject.toml" if exist "%START_DIR%\src\testforge" (
    set "REPO_ROOT=%START_DIR%"
    echo [OK] Repositorio local detectado em %START_DIR%
    echo [OK] Repositorio local detectado em %START_DIR% >> "%LOG_FILE%"
)

if not defined REPO_ROOT (
    set "REPO_ROOT=%DEFAULT_CLONE_ROOT%"
    echo [INFO] Usando pasta curta para clone - compatibilidade com nomes longos: !REPO_ROOT!
    echo [INFO] Usando pasta curta para clone: !REPO_ROOT! >> "%LOG_FILE%"

    if not exist "%CLONE_BASE%" (
        mkdir "%CLONE_BASE%" >> "%LOG_FILE%" 2>&1
        if errorlevel 1 (
            echo [WARN] Nao foi possivel criar %CLONE_BASE%. Tentando fallback em %CLONE_BASE_FALLBACK%...
            echo [WARN] Nao foi possivel criar %CLONE_BASE%. Tentando fallback em %CLONE_BASE_FALLBACK%... >> "%LOG_FILE%"
            set "CLONE_BASE=%CLONE_BASE_FALLBACK%"
            set "REPO_ROOT=!CLONE_BASE!\%REPO_DIR_NAME%"
            if not exist "!CLONE_BASE!" (
                mkdir "!CLONE_BASE!" >> "%LOG_FILE%" 2>&1
                if errorlevel 1 (
                    set "FAIL_REASON=Nao foi possivel criar pasta de clone em %CLONE_BASE% nem em %CLONE_BASE_FALLBACK%."
                    echo [ERRO] !FAIL_REASON!
                    echo [ERRO] !FAIL_REASON! >> "%LOG_FILE%"
                    exit /b 1
                )
            )
            echo [INFO] Fallback de pasta de clone ativo: !CLONE_BASE!
            echo [INFO] Fallback de pasta de clone ativo: !CLONE_BASE! >> "%LOG_FILE%"
        )
    )

    if exist "!REPO_ROOT!\.git" (
        echo [OK] Repositorio ja existe em !REPO_ROOT!
        echo [OK] Repositorio ja existe em !REPO_ROOT! >> "%LOG_FILE%"
    ) else (
        if exist "!REPO_ROOT!" (
            echo [ERRO] A pasta !REPO_ROOT! ja existe, mas nao e um repositorio Git valido.
            echo [ERRO] Pasta existente sem .git: !REPO_ROOT! >> "%LOG_FILE%"
            exit /b 1
        )
        echo [INFO] Pasta destino do clone: !REPO_ROOT!
        echo [INFO] Pasta destino do clone: !REPO_ROOT! >> "%LOG_FILE%"
        echo [INFO] Clonando repositorio principal...
        echo [INFO] Clonando repositorio principal em !REPO_ROOT! >> "%LOG_FILE%"
        git -c core.longpaths=true clone "%REPO_URL%" "!REPO_ROOT!" >> "%LOG_FILE%" 2>&1
        if errorlevel 1 (
            set "FAIL_REASON=Falha ao clonar o repositorio em !REPO_ROOT!."
            echo [ERRO] Falha ao clonar o repositorio.
            echo [ERRO] Falha ao clonar o repositorio. >> "%LOG_FILE%"
            exit /b 1
        )
    )
)

cd /d "%REPO_ROOT%" >nul 2>&1
if errorlevel 1 (
    set "FAIL_REASON=Nao foi possivel acessar a pasta do repositorio: %REPO_ROOT%"
    echo [ERRO] Nao foi possivel acessar a pasta do repositorio: %REPO_ROOT%
    echo [ERRO] Nao foi possivel acessar a pasta do repositorio: %REPO_ROOT% >> "%LOG_FILE%"
    exit /b 1
)

echo [INFO] Selecionando branch %TARGET_BRANCH%...
echo [INFO] Selecionando branch %TARGET_BRANCH% >> "%LOG_FILE%"
git config core.longpaths true >> "%LOG_FILE%" 2>&1
git fetch origin "%TARGET_BRANCH%" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    set "FAIL_REASON=Falha ao buscar a branch %TARGET_BRANCH% no remoto."
    echo [ERRO] Falha ao buscar a branch %TARGET_BRANCH% no remoto.
    echo [ERRO] Falha ao buscar a branch %TARGET_BRANCH% no remoto. >> "%LOG_FILE%"
    exit /b 1
)

git checkout "%TARGET_BRANCH%" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    set "FAIL_REASON=Falha ao trocar para a branch %TARGET_BRANCH%."
    echo [ERRO] Falha ao trocar para a branch %TARGET_BRANCH%.
    echo [ERRO] Falha ao trocar para a branch %TARGET_BRANCH%. >> "%LOG_FILE%"
    exit /b 1
)

git pull --ff-only origin "%TARGET_BRANCH%" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    set "FAIL_REASON=Falha ao atualizar a branch %TARGET_BRANCH%."
    echo [ERRO] Falha ao atualizar a branch %TARGET_BRANCH%.
    echo [ERRO] Falha ao atualizar a branch %TARGET_BRANCH%. >> "%LOG_FILE%"
    exit /b 1
)

echo [OK] Repositorio pronto na branch %TARGET_BRANCH%.
echo [OK] Repositorio pronto na branch %TARGET_BRANCH%. >> "%LOG_FILE%"
exit /b 0

:install_from_public_pypi
"%VENV_PY%" -m ensurepip --upgrade >> "%LOG_FILE%" 2>&1
"%VENV_PY%" -m pip install --upgrade pip setuptools wheel %PIP_PUBLIC_ARGS% >> "%LOG_FILE%" 2>&1
if errorlevel 1 exit /b 1
"%VENV_PY%" -m pip install -e "%INSTALL_EXTRAS%" %PIP_PUBLIC_ARGS% >> "%LOG_FILE%" 2>&1
exit /b %ERRORLEVEL%

:install_from_wheelhouse
"%VENV_PY%" -m ensurepip --upgrade >> "%LOG_FILE%" 2>&1
"%VENV_PY%" -m pip install --no-index --find-links "%WHEELHOUSE%" --upgrade pip setuptools wheel >> "%LOG_FILE%" 2>&1
if errorlevel 1 exit /b 1
"%VENV_PY%" -m pip install --no-index --find-links "%WHEELHOUSE%" -e "%INSTALL_EXTRAS%" >> "%LOG_FILE%" 2>&1
exit /b %ERRORLEVEL%

:create_desktop_shortcut
setlocal EnableExtensions EnableDelayedExpansion

set "TARGET_BAT=%REPO_ROOT_FINAL%\testforge-recorder.bat"
if not exist "%TARGET_BAT%" (
    echo [WARN] Nao encontrei %TARGET_BAT%. Atalho da area de trabalho nao sera criado.
    echo [WARN] Nao encontrei %TARGET_BAT%. Atalho nao criado. >> "%LOG_FILE%"
    endlocal & exit /b 1
)

rem 1) Copiar icone para local persistente, se disponivel junto ao instalador
set "ICON_SRC=%INSTALLER_DIR%\testforge.ico"
set "ICON_PERSIST=%CLONE_BASE%\testforge.ico"
if exist "%ICON_SRC%" (
    if not exist "%CLONE_BASE%" mkdir "%CLONE_BASE%" >> "%LOG_FILE%" 2>&1
    copy /Y "%ICON_SRC%" "%ICON_PERSIST%" >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        echo [WARN] Nao foi possivel copiar o icone para %ICON_PERSIST%. >> "%LOG_FILE%"
    ) else (
        echo [OK] Icone copiado para %ICON_PERSIST% >> "%LOG_FILE%"
    )
)

rem 2) Resolver caminho do icone por prioridade
set "ICON_PATH="
if exist "%REPO_ROOT_FINAL%\assets\testforge.ico" set "ICON_PATH=%REPO_ROOT_FINAL%\assets\testforge.ico"
if not defined ICON_PATH if exist "%REPO_ROOT_FINAL%\testforge.ico" set "ICON_PATH=%REPO_ROOT_FINAL%\testforge.ico"
if not defined ICON_PATH if exist "%ICON_PERSIST%" set "ICON_PATH=%ICON_PERSIST%"
if not defined ICON_PATH set "ICON_PATH=%SystemRoot%\System32\imageres.dll"

echo [INFO] Icone selecionado: %ICON_PATH% >> "%LOG_FILE%"

rem 3) Criar atalho via PowerShell (usa a pasta Desktop real, mesmo com OneDrive)
set "PS_SCRIPT=%TEMP%\_tf_shortcut_%RANDOM%.ps1"
> "%PS_SCRIPT%" echo $ErrorActionPreference = 'Stop'
>> "%PS_SCRIPT%" echo $desktop  = [Environment]::GetFolderPath('Desktop')
>> "%PS_SCRIPT%" echo $lnkPath  = Join-Path $desktop '%SHORTCUT_NAME%'
>> "%PS_SCRIPT%" echo $wsh      = New-Object -ComObject WScript.Shell
>> "%PS_SCRIPT%" echo $s        = $wsh.CreateShortcut($lnkPath)
>> "%PS_SCRIPT%" echo $s.TargetPath       = '%TARGET_BAT%'
>> "%PS_SCRIPT%" echo $s.WorkingDirectory = '%REPO_ROOT_FINAL%'
>> "%PS_SCRIPT%" echo $s.Description      = 'Abrir TestForge Recorder (CAIXA)'
>> "%PS_SCRIPT%" echo $s.WindowStyle      = 1
>> "%PS_SCRIPT%" echo if ('%ICON_PATH%' -like '*imageres.dll*') { $s.IconLocation = '%ICON_PATH%,109' } else { $s.IconLocation = '%ICON_PATH%,0' }
>> "%PS_SCRIPT%" echo $s.Save()
>> "%PS_SCRIPT%" echo Write-Host ('Atalho criado em: ' + $lnkPath)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" >> "%LOG_FILE%" 2>&1
set "PS_RC=%ERRORLEVEL%"
del /q "%PS_SCRIPT%" >nul 2>&1

if not "%PS_RC%"=="0" (
    echo [WARN] Falha ao criar atalho na Area de Trabalho. Instalacao continua valida.
    echo [WARN] Falha ao criar atalho na Area de Trabalho (rc=%PS_RC%). >> "%LOG_FILE%"
    endlocal & exit /b 1
)

echo [OK] Atalho da Area de Trabalho criado: %SHORTCUT_NAME%
echo [OK] Atalho da Area de Trabalho criado: %SHORTCUT_NAME% >> "%LOG_FILE%"
endlocal & set "SHORTCUT_OK=1"
exit /b 0

:success
call :log "Criando atalho na Area de Trabalho"
call :create_desktop_shortcut

echo.
echo ==========================================================
echo  [OK] Ambiente pronto.
echo ==========================================================
echo.
echo O TestForge foi instalado com sucesso.
echo.
echo Pasta do projeto:
echo %REPO_ROOT_FINAL%
echo.
if "%SHORTCUT_OK%"=="1" (
    echo Atalho criado na Area de Trabalho:
    echo    %SHORTCUT_NAME%
    echo De duplo clique nele para abrir o TestForge Recorder.
) else (
    echo Nao foi possivel criar o atalho na Area de Trabalho automaticamente.
    echo Voce pode abrir a GUI executando manualmente:
    echo    %REPO_ROOT_FINAL%\testforge-recorder.bat
)
echo.
echo Log salvo em:
echo %LOG_FILE%
echo.
echo [OK] Ambiente pronto. >> "%LOG_FILE%"
echo Fim: %DATE% %TIME% >> "%LOG_FILE%"
pause
exit /b 0

:fatal
echo.
echo ==========================================================
echo  [FALHA] Nao foi possivel concluir a instalacao.
echo ==========================================================
echo.
echo O instalador tentou automaticamente:
echo  1. Repositorio interno CAIXA
echo  2. Pasta local wheelhouse, se existir
echo  3. PyPI publico, para uso pela fabrica quando permitido
if defined FAIL_REASON (
echo.
echo Motivo identificado:
echo %FAIL_REASON%
)
echo.
echo Verifique o log detalhado em:
echo %LOG_FILE%
echo.
echo Possiveis causas:
echo - Python nao instalado ou fora do PATH.
echo - Rede/VPN CAIXA sem acesso ao binario.caixa.
echo - Ambiente da fabrica sem acesso ao PyPI publico.
echo - Proxy/certificado corporativo nao configurado.
echo - Git ausente quando alguma dependencia exigir git+https.
echo - Pacote inexistente no repositorio interno e ausente na wheelhouse.
echo.
echo [FALHA] Instalacao nao concluida. >> "%LOG_FILE%"
echo Fim: %DATE% %TIME% >> "%LOG_FILE%"
pause
exit /b 1

:log
echo [INFO] %~1 >> "%LOG_FILE%"
exit /b 0
