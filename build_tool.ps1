# 自动打包：干净 venv + PyInstaller onefile -> 资产Review表格工具-Windows\
# 由 自动打包工具.bat（ASCII 启动器）调用；本文件必须保存为 UTF-8 with BOM。
$ErrorActionPreference = "Stop"

function Find-Python {
    foreach ($c in @("python", "py")) {
        $found = Get-Command $c -ErrorAction SilentlyContinue
        if ($found) { return $found.Source }
    }
    return $null
}

Write-Host "[1/4] 探测 Python ..."
$py = Find-Python
if (-not $py) {
    Write-Host "[错误] 未找到 Python，请先安装 Python 3.9+，或运行 启动.bat 自动安装。" -ForegroundColor Red
    exit 1
}
Write-Host "  使用: $py"

Write-Host "[2/4] 准备虚拟环境 .venv-build ..."
$venv = Join-Path $PSScriptRoot ".venv-build"
$venvPy = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    if (Test-Path $venv) { Remove-Item $venv -Recurse -Force }
    & $py -m venv $venv
    if ($LASTEXITCODE -ne 0) { Write-Host "[错误] venv 创建失败" -ForegroundColor Red; exit 1 }
}

Write-Host "[3/4] 安装依赖与 PyInstaller ..."
& $venvPy -m pip install --upgrade pip | Out-Null
& $venvPy -m pip install -r (Join-Path $PSScriptRoot "requirements.txt") pyinstaller | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "[错误] 依赖安装失败" -ForegroundColor Red; exit 1 }

Write-Host "[4/4] PyInstaller 打包（onefile，内置 HDR 与渲染脚本）..."
Set-Location $PSScriptRoot
& $venvPy -m PyInstaller --onefile --windowed --noconfirm --clean `
    --name "资产Review表格工具" `
    --add-data "blender_script.py;." `
    --add-data "aristea_wreck_puresky_1k.hdr;." `
    main.py
if ($LASTEXITCODE -ne 0) { Write-Host "[错误] 打包失败" -ForegroundColor Red; exit 1 }

Write-Host "[5/5] 复制到交付目录 ..."
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$delivery = Join-Path $PSScriptRoot "资产Review表格工具-Windows"
New-Item -ItemType Directory -Force -Path $delivery | Out-Null
$portable = Join-Path $delivery "资产Review表格工具-portable-$stamp.exe"
Copy-Item (Join-Path $PSScriptRoot "dist\资产Review表格工具.exe") $portable -Force

Write-Host ""
Write-Host "[完成] $portable" -ForegroundColor Green
Write-Host "双击即用；Blender 仍需已安装，HDR 已内置，可在 exe 旁放 assets\hdri\*.hdr 覆盖。"
