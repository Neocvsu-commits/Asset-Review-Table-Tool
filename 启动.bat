@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
cd /d "%~dp0"

set "PY_CMD="
call :detect_python
if defined PY_CMD goto have_python

echo.
echo ============================================================
echo  Python 3.9+ not detected on this PC.
echo  Will try to install Python 3.11 automatically.
echo  This usually takes 1-3 minutes (network + UAC may prompt).
echo ============================================================
echo.

call :install_python_winget
call :detect_python
if defined PY_CMD goto have_python

call :install_python_download
call :detect_python
if defined PY_CMD goto have_python

echo.
echo [ERROR] Could not install Python automatically.
echo Please install Python 3.11+ manually:
echo   https://www.python.org/downloads/
echo (Tick "Add python.exe to PATH" during install.)
echo Then double-click this file again.
start "" https://www.python.org/downloads/
pause
exit /b 1

:have_python
%PY_CMD% -c "import openpyxl, PIL, tkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing Python packages: openpyxl, pillow ...
    %PY_CMD% -m pip install --disable-pip-version-check -r "%~dp0requirements.txt"
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] pip install failed. Run manually:
        echo   %PY_CMD% -m pip install -r requirements.txt
        pause
        exit /b 1
    )
)

%PY_CMD% "%~dp0main.py" %*
set "EXITCODE=%errorlevel%"
if not "%EXITCODE%"=="0" (
    echo.
    echo [ERROR] main.py exit code: %EXITCODE%
    pause
)
exit /b %EXITCODE%


:detect_python
set "PY_CMD="
py -3 -c "import sys;raise SystemExit(0 if sys.version_info>=(3,9) else 1)" >nul 2>&1
if %errorlevel%==0 (
    set "PY_CMD=py -3"
    exit /b 0
)
python -c "import sys;raise SystemExit(0 if sys.version_info>=(3,9) else 1)" >nul 2>&1
if %errorlevel%==0 (
    set "PY_CMD=python"
    exit /b 0
)
REM Fallback: probe well-known per-user / per-machine install paths
REM (helpful right after winget/installer finishes but PATH is not yet refreshed)
for %%V in (313 312 311 310 39) do (
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
        set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
        exit /b 0
    )
    if exist "%ProgramFiles%\Python%%V\python.exe" (
        set "PY_CMD=%ProgramFiles%\Python%%V\python.exe"
        exit /b 0
    )
)
exit /b 1


:install_python_winget
where winget >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] winget not available, will try direct download.
    exit /b 1
)
echo [INFO] Installing Python 3.11 via winget ...
winget install --id Python.Python.3.11 -e --accept-package-agreements --accept-source-agreements --silent
if %errorlevel% neq 0 (
    echo [WARN] winget install returned code %errorlevel%.
    exit /b 1
)
echo [OK] winget install finished.
exit /b 0


:install_python_download
where powershell >nul 2>&1
if %errorlevel% neq 0 exit /b 1
set "INSTALLER=%TEMP%\python-3.11-installer.exe"
set "PYURL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
echo [INFO] Downloading Python 3.11.9 installer from python.org ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; try { (New-Object Net.WebClient).DownloadFile('%PYURL%','%INSTALLER%'); exit 0 } catch { Write-Host $_; exit 1 }"
if %errorlevel% neq 0 (
    echo [WARN] Download failed. Check network connection.
    exit /b 1
)
echo [INFO] Running installer (per-user, silent; UAC may prompt) ...
"%INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_pip=1
set "EC=%errorlevel%"
del "%INSTALLER%" >nul 2>&1
if not "%EC%"=="0" (
    echo [WARN] Installer exit code %EC%.
)
exit /b %EC%
