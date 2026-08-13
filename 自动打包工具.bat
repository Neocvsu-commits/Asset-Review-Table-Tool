@echo off
chcp 65001 >nul
setlocal

REM ─── 自动打包：干净 venv + PyInstaller onefile → 资产Review表格工具-Windows\ ───

set "PY="
for %%V in (python py) do (
    where %%V >nul 2>nul
    if not errorlevel 1 set "PY=%%V"
)
if not defined PY (
    echo [错误] 未找到 Python，请先安装 Python 3.9+，或运行 启动.bat 自动安装。
    exit /b 1
)

echo [1/4] 使用 %PY% 创建干净虚拟环境 .venv-build ...
if exist .venv-build rmdir /s /q .venv-build
%PY% -m venv .venv-build || ( echo [错误] venv 创建失败 & exit /b 1 )
call .venv-build\Scripts\activate.bat

echo [2/4] 安装依赖与 PyInstaller ...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt pyinstaller >nul || ( echo [错误] 依赖安装失败 & exit /b 1 )

echo [3/4] PyInstaller 打包（onefile，内置 HDR 与渲染脚本）...
pyinstaller --onefile --windowed --noconfirm --clean ^
  --name 资产Review表格工具 ^
  --add-data "blender_script.py;." ^
  --add-data "aristea_wreck_puresky_1k.hdr;." ^
  main.py || ( echo [错误] 打包失败 & exit /b 1 )

echo [4/4] 复制到交付目录 ...
for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "STAMP=%%i"
if not exist "资产Review表格工具-Windows" mkdir "资产Review表格工具-Windows"
copy /y "dist\资产Review表格工具.exe" "资产Review表格工具-Windows\资产Review表格工具-portable-%STAMP%.exe" >nul

echo.
echo [完成] 资产Review表格工具-Windows\资产Review表格工具-portable-%STAMP%.exe
echo 双击即用；Blender 仍需已安装，HDR 已内置，可在 exe 旁放 assets\hdri\*.hdr 覆盖。
endlocal
