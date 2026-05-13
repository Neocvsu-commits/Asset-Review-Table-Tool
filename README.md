# 资产 Review 表格工具

扫描资产文件夹，读取 `*_BasicInformation.csv` 元数据并用 Blender 渲染缩略图，
最终生成一份带嵌入图片的 Excel 报表（`xlsx`）。

## 目录结构

```
输出工具/
├── README.md           本文
├── requirements.txt    Python 依赖（openpyxl, pillow）
├── 启动.bat            Windows 一键启动（自动安装依赖并打开 GUI）
├── main.py             GUI / CLI 统一入口
├── gui.py              Tk 图形界面
├── builder.py          扫描目录 → 渲染 → 写 xlsx
├── renderer.py         Blender 子进程调度
├── blender_script.py   在 Blender 内运行的渲染脚本
├── utils.py            CSV 解析、Blender 探测等通用工具
└── assets/hdri/        可选 HDR 环境贴图（见该目录内 README）
```

## 环境准备

- Windows 10/11
- **Blender 4.2 LTS**（脚本针对 4.2 调优；如装了 5.x 截图发白请改用 4.2）  
  解压绿色版或安装包均可，工具会自动从盘符根目录、用户目录、`Program Files`、Steam、注册表等位置探测。
- **Python 3.9+**：双击 `启动.bat` 时若未检测到 Python，会自动尝试：  
  1. `winget install Python.Python.3.11`（Win10 1809+/Win11 自带）  
  2. winget 不可用时从 `python.org` 下载官方安装器静默安装（per-user, 自动加入 PATH）  
  3. 都失败时打开下载页提示手动安装  

  也可以手动从 <https://www.python.org/downloads/> 安装，记得勾选 *Add python.exe to PATH*。

## 资产目录约定

`资产根目录/<资产名>/` 下应至少包含：

- 任意名称的 `*_BasicInformation.csv`（第一行表头，第二行起为「键,值」对）
- 至少一个 `.fbx` 或 `.glb`（用于渲染缩略图，优先 GLB）

## 使用方法

### 方式一：图形界面（推荐）

双击 `启动.bat`，按界面提示：

1. 「添加文件夹…」选择一个或多个资产根目录
2. 确认输出目录（默认在桌面 `资产Review导出`）
3. 「自动查找」或「浏览」选择 `blender.exe`
4. 点「开始生成表格」

完成后输出目录中会出现：

- `资产review归档_全量_YYYYMMDD.xlsx`（单根目录）或 `_合并_` 版（多根）
- `thumbnails/` 子目录（所有缩略图）
- `_render_errors.log`（仅在渲染失败时写入；每次运行会清空重写）

### 方式二：命令行

```powershell
py -3 main.py --cli ^
    --assets-root D:\AssetsA ^
    --assets-root D:\AssetsB ^
    --out-dir D:\Review ^
    --blender "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
```

可选参数：

- `--hdr <file>`：指定环境 HDR（不指定则使用 `assets/hdri/` 内置文件，若不存在则不加载）
- `--count N --seed S`：随机抽样 N 个资产作为测试样例（默认全量）

## 表格列

资产名称 / 中文名称 / 骨骼 / 动画 / 动画类型 / 模型截图 /
三角面数 / 材质球数量 / 贴图数量 / 贴图尺寸（去重摘要）/
贴图文件总大小（散文件）/ FBX 文件大小 / GLB 文件大小 / 是否入库

## 常见问题

- **截图发白**：优先在资产文件夹中放置带贴图的 `.glb`；仅有 `.fbx` 时请保证贴图与 fbx 在同一目录。
- **多根目录中资产重名**：以「先添加的根目录」为准，后续同名资产会跳过并在日志提示。
- **渲染失败**：查看输出目录下 `_render_errors.log`，包含 Blender/Python 报错详情；
  脚本会先尝试 EEVEE，失败时自动用 Cycles（CPU）重试一次。
