# 资产 Review 表格工具

扫描资产目录 → 自动渲染缩略图 → 生成带截图的 Excel 报表。外包回收验收、资产盘点时，不用手动截图贴表。

## 解决的问题

几十上百个资产要做 review，逐个打开 Blender 截图、复制面数和贴图信息、粘贴到 Excel——做完一遍半天没了。

这个工具帮你自动跑完：读取资产目录下的 BasicInformation.csv 元数据，调 Blender 渲染缩略图，输出一份 xlsx 报表，截图直接嵌在表格里。

## 环境要求

| 项目 | 要求 |
| :--- | :--- |
| 系统 | Windows 10/11 |
| Blender | 4.2 LTS（推荐，5.x 截图发白请换 4.2） |
| Python | 3.9+ |

双击 `启动.bat` 时如果没检测到 Python，会自动尝试 winget 安装；winget 不可用时从 python.org 下载静默安装。Blender 路径工具会自动从盘符根目录、用户目录、Program Files、Steam、注册表等位置探测，不用手动配。

## 资产目录约定

每个资产的文件夹下需要：

- 一份 `*_BasicInformation.csv`（第一行为表头，第二行起为「键,值」对）
- 至少一个 `.fbx` 或 `.glb`（用于渲染缩略图，优先 GLB）

```
资产根目录/
├── 资产A/
│   ├── 资产A_BasicInformation.csv
│   └── 资产A.glb
├── 资产B/
│   ├── 资产B_BasicInformation.csv
│   └── 资产B.fbx
└── ...
```

## 快速上手

### 图形界面（推荐）

双击 `启动.bat`，然后：

1. 点「添加文件夹…」选一个或多个资产根目录
2. 确认输出目录（默认在桌面 `资产Review导出`）
3. 点「自动查找」或「浏览」选 `blender.exe`
4. 点「开始生成表格」

输出目录会生成：

- `资产review归档_全量_YYYYMMDD.xlsx`（单根目录）或 `_合并_` 版（多根）
- `thumbnails/` 子目录（所有缩略图）
- `_render_errors.log`（仅在渲染失败时写入）

### 命令行

```powershell
py -3 main.py --cli `
    --assets-root D:\AssetsA `
    --assets-root D:\AssetsB `
    --out-dir D:\Review `
    --blender "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
```

可选参数：
- `--hdr <file>`：指定环境 HDR（不指定则用 `assets/hdri/` 内置文件）
- `--count N --seed S`：随机抽样 N 个资产作为测试样例（默认全量）

## 表格包含的列

资产名称 / 中文名称 / 骨骼 / 动画 / 动画类型 / 模型截图 / 三角面数 / 材质球数量 / 贴图数量 / 贴图尺寸（去重摘要）/ 贴图文件总大小（散文件）/ FBX 文件大小 / GLB 文件大小 / 是否入库

## FAQ

**Q1：截图发白？**
优先在资产文件夹里放带贴图的 `.glb`。只有 `.fbx` 时保证贴图和 fbx 在同一目录。渲染会先试 EEVEE，失败后自动用 Cycles（CPU）重试一次。

**Q2：多根目录里资产重名？**
以先添加的根目录为准，后续同名资产跳过，日志里会提示。

**Q3：渲染失败怎么看原因？**
看输出目录下的 `_render_errors.log`，包含 Blender/Python 的完整报错。

**Q4：Blender 装了其他版本，工具能找到吗？**
工具自动从盘符根目录、用户目录、Program Files、Steam、注册表等位置探测。没找到也可以手动点「浏览」指定 `blender.exe`。
