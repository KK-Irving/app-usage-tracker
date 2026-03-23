# 📱 App Usage Tracker V2 — 应用使用时间追踪器

一个基于 Python 的 Windows 应用使用时间追踪工具。自动采集进程数据，智能分类应用，生成多维度分析报告，帮助你了解时间去向、提升工作效率。

V2 版本新增：前台窗口检测、目标设定与达成率、应用切换分析、Web 仪表盘、多设备同步、项目级追踪、智能建议、休息提醒、SQLite 数据库后端、系统托盘常驻。

## 安装

```bash
# 克隆项目
git clone https://github.com/KK-Irving/app-usage-tracker.git
cd app-usage-tracker

# 一键安装所有依赖
pip install -r requirements.txt
```

安装完成后即可使用全部功能。如需 S3 同步，编辑 `requirements.txt` 取消 `boto3` 的注释后重新安装。

## 功能概览

### V1 核心功能

| 功能 | 说明 |
|------|------|
| 🔄 数据采集 | 通过 psutil 获取进程信息，记录应用名称、CPU、内存、运行时长 |
| 🏷️ 智能分类 | 自动将应用归类为 开发/工作/社交/娱乐/系统/其他，支持自定义规则 |
| 📊 每日报告 | 总览、分类汇总、Top 10、时间块分布、专注力、碎片时间、建议等 |
| 📈 周报/月报 | 聚合多日数据，与上周/上月对比，展示趋势变化 |
| 🎯 专注力追踪 | 检测深度工作时段，计算专注度分数（0-100），支持番茄钟计时 |
| ⏱️ 碎片时间分析 | 识别短时间使用，三级分类，给出利用建议 |
| ⏰ 超时提醒 | 应用使用超过阈值时发送 Windows Toast 通知 |
| 📤 数据导出 | 导出 CSV（utf-8-sig 编码），支持单日/周/月导出 |
| 📉 可视化图表 | matplotlib 生成分类饼图、活跃度柱状图、周趋势折线图 |
| ⏲️ 定时任务 | 通过 Windows 任务计划程序自动执行采集和报告 |

### V2 新增功能

| 功能 | 说明 |
|------|------|
| 🖥️ 前台窗口检测 | 通过 win32gui 区分前台活跃和后台运行，精确追踪实际使用 |
| 🎯 目标设定 | 设定每日使用目标（如"开发 ≥ 4h"），追踪达成率和趋势 |
| 🔄 切换分析 | 统计应用切换频率、上下文切换成本、Top 切换对 |
| 🌐 Web 仪表盘 | Flask 本地 Web 界面，ECharts 交互式图表，日期/分类筛选 |
| ☁️ 多设备同步 | 本地文件夹或 S3 同步，跨设备汇总报告 |
| 📁 项目追踪 | VS Code 窗口标题解析，按项目维度统计时间 |
| 💡 智能建议 | 基于 7 天历史数据识别效率模式，生成个性化建议 |
| 🔔 休息提醒 | 20-20-20 法则 + 长休息提醒，基于前台检测判断连续工作 |
| 🗄️ SQLite 后端 | 从 JSON 迁移到 SQLite，支持复杂查询，零外部依赖 |
| 🔲 系统托盘 | pystray 托盘常驻，实时显示当前应用和今日时长 |

## 环境要求

- Python 3.8+
- Windows 操作系统

### 依赖库

| 依赖 | 用途 | 必需/可选 |
|------|------|-----------|
| psutil | 进程数据采集 | 必需 |
| pywin32 | 前台窗口检测 | 推荐（缺失时自动降级） |
| flask | Web 仪表盘 | 推荐（仅 web 命令需要） |
| pystray + Pillow | 系统托盘 | 推荐（仅 tray 命令需要） |
| matplotlib | 可视化图表 | 推荐（仅 chart 命令需要） |
| boto3 | S3 同步 | 可选（仅 S3 同步需要） |

```bash
# 一键安装全部依赖（推荐）
pip install -r requirements.txt
```

## 快速开始

```bash
# 1. 采集一次数据
python app_usage_tracker.py collect

# 2. 生成今日报告
python app_usage_tracker.py daily

# 3. 启动 Web 仪表盘
python app_usage_tracker.py web

# 4. 启动系统托盘（后台常驻）
python app_usage_tracker.py tray

# 5. 从 V1 JSON 迁移到 SQLite
python app_usage_tracker.py migrate
```

## 项目结构

```
app-usage-tracker/
├── app_usage_tracker.py          # 统一命令行入口（V1 + V2 所有命令）
├── app_categories.py             # 统一分类引擎
├── config.json                   # 全局配置
├── requirements.txt              # pip 依赖清单
├── check_cpu.py                  # CPU 占用快速检查工具
├── get_usage.py                  # 即时应用使用统计
├── get_usage_by_time.py          # 时间段分布分析
├── config/
│   ├── app_categories.json       # 应用分类规则
│   ├── timeout_alerts.json       # 超时提醒配置（首次使用时自动创建）
│   ├── usage_goals.json          # 目标配置（首次使用时自动创建）
│   ├── projects.json             # 项目映射（首次使用时自动创建）
│   ├── break_rules.json          # 休息规则（首次使用时自动创建）
│   └── sync_config.json          # 同步配置（首次使用时自动创建）
├── scripts/
│   ├── collect_usage.py          # 数据采集（V2 增强：DataStore + 前台字段）
│   ├── collect_usage_v2.py       # V2 独立采集脚本（DataStore 直写）
│   ├── get_daily_report.py       # 每日报告（V2 增强：目标/切换/项目/建议）
│   ├── analyze_trends.py         # 周报/月报（V2 增强：目标趋势）
│   ├── focus_tracker.py          # 专注力追踪（V2 增强：DataStore + 切换相关性）
│   ├── fragment_analyzer.py      # 碎片时间分析
│   ├── timeout_alert.py          # 超时提醒（Toast 通知）
│   ├── export_data.py            # CSV 数据导出
│   ├── visualizer.py             # 可视化图表（matplotlib）
│   ├── scheduler.py              # Windows 定时任务调度
│   ├── data_store.py             # 统一数据访问层（SQLite/JSON 双后端）
│   ├── db_migrate.py             # JSON→SQLite 迁移工具
│   ├── foreground_detector.py    # 前台窗口检测（win32gui）
│   ├── goal_manager.py           # 目标设定与达成率管理
│   ├── switch_analyzer.py        # 应用切换频率分析
│   ├── project_tracker.py        # 项目级时间追踪
│   ├── suggestion_engine.py      # 智能建议引擎
│   ├── break_reminder.py         # 休息提醒（20-20-20 法则）
│   ├── sync_manager.py           # 多设备数据同步
│   ├── web_dashboard.py          # Web 仪表盘（Flask + ECharts）
│   └── tray_app.py               # 系统托盘常驻（pystray）
├── templates/                    # Web 仪表盘 HTML 模板
│   ├── base.html                 # 基础布局
│   ├── dashboard.html            # 首页仪表盘
│   └── goals.html                # 目标达成率页面
├── data/
│   ├── usage_tracker.db          # SQLite 数据库
│   ├── usage_YYYY-MM-DD.json     # V1 每日数据（JSON 模式）
│   ├── focus_sessions.json       # 专注会话数据
│   ├── suggestions_cache.json    # 智能建议缓存
│   └── reports/                  # 生成的报告和图表
├── tests/
│   └── test_db_migrate.py        # 迁移工具测试
├── LICENSE                       # MIT 许可证
├── SKILL.md                      # 技能描述文件
└── README.md                     # 项目说明文档
```

## 命令详解

所有功能通过 `python app_usage_tracker.py <命令>` 访问。

### V1 命令

| 命令 | 说明 | 示例 |
|------|------|------|
| collect | 采集当前应用数据 | `python app_usage_tracker.py collect` |
| daily | 生成每日报告 | `python app_usage_tracker.py daily --date 2026-03-19` |
| weekly | 生成周报 | `python app_usage_tracker.py weekly` |
| monthly | 生成月报 | `python app_usage_tracker.py monthly` |
| focus | 专注力分析/番茄钟 | `python app_usage_tracker.py focus --timer 25` |
| fragments | 碎片时间分析 | `python app_usage_tracker.py fragments` |
| export | 数据导出 CSV | `python app_usage_tracker.py export --weekly` |
| categories | 管理应用分类 | `python app_usage_tracker.py categories add 工作 notion` |
| timeout | 超时提醒 | `python app_usage_tracker.py timeout --check` |
| chart | 可视化图表 | `python app_usage_tracker.py chart --pie` |
| schedule | 定时任务管理 | `python app_usage_tracker.py schedule --setup-all` |

### V2 新增命令

| 命令 | 说明 | 示例 |
|------|------|------|
| goals | 目标管理 | `python app_usage_tracker.py goals --add 开发 min 240` |
| switches | 切换分析 | `python app_usage_tracker.py switches --date 2026-03-19` |
| projects | 项目管理 | `python app_usage_tracker.py projects --add myproject E:/projects/myproject` |
| web | 启动 Web 仪表盘 | `python app_usage_tracker.py web` |
| sync | 多设备同步 | `python app_usage_tracker.py sync --push` |
| break | 休息提醒 | `python app_usage_tracker.py break --start` |
| tray | 启动系统托盘 | `python app_usage_tracker.py tray` |
| migrate | JSON→SQLite 迁移 | `python app_usage_tracker.py migrate --dry-run` |

### goals — 目标管理

```bash
python app_usage_tracker.py goals --add 开发 min 240   # 开发类 ≥ 240 分钟
python app_usage_tracker.py goals --add 社交 max 60    # 社交类 ≤ 60 分钟
python app_usage_tracker.py goals --list               # 查看目标及达成状态
python app_usage_tracker.py goals --evaluate           # 评估今日达成率
python app_usage_tracker.py goals --remove 社交        # 移除目标
```

### switches — 切换分析

```bash
python app_usage_tracker.py switches                   # 分析今日切换
python app_usage_tracker.py switches --date 2026-03-19 # 分析指定日期
```

输出：总切换次数、上下文切换成本（分钟）、高频切换时段、Top 切换对。

### projects — 项目管理

```bash
python app_usage_tracker.py projects --add myproject E:/projects/myproject
python app_usage_tracker.py projects --list
python app_usage_tracker.py projects --report
python app_usage_tracker.py projects --remove myproject
```

项目检测策略：VS Code 窗口标题解析 → 终端 cwd 检测 → 路径前缀匹配。

### web — Web 仪表盘

```bash
python app_usage_tracker.py web
```

默认监听 `http://127.0.0.1:8080`，提供首页仪表盘、目标达成率页面、RESTful API、ECharts 交互式图表。

### sync — 多设备同步

```bash
python app_usage_tracker.py sync --push    # 推送到远程
python app_usage_tracker.py sync --pull    # 拉取所有设备数据
python app_usage_tracker.py sync --report  # 跨设备汇总报告
```

需先在 `config/sync_config.json` 配置 `remote_path`（首次执行 sync 命令时自动创建配置文件）。

### break — 休息提醒

```bash
python app_usage_tracker.py break --start              # 启动监控
python app_usage_tracker.py break --list               # 查看规则
python app_usage_tracker.py break --add 45 5 "休息5分钟" # 添加规则
```

默认规则：20-20-20 法则（20 分钟工作 → 20 秒休息）+ 90 分钟长休息。

### tray — 系统托盘

```bash
python app_usage_tracker.py tray
```

托盘图标实时显示当前应用和今日时长，右键菜单提供报告、Web 仪表盘、采集、退出等操作。

### migrate — 数据迁移

```bash
python app_usage_tracker.py migrate --dry-run  # 预览迁移数据量
python app_usage_tracker.py migrate            # 执行 JSON→SQLite 迁移
```

## 独立工具脚本

除统一入口外，项目根目录还提供几个可独立运行的快捷工具：

| 脚本 | 说明 |
|------|------|
| `get_usage.py` | 即时统计当前应用使用情况（按应用汇总内存、CPU 峰值、运行时长） |
| `get_usage_by_time.py` | 按时间段分析应用分布（小时分布、时间块分布） |
| `check_cpu.py` | 快速检查当前 CPU 占用情况 |

```bash
python get_usage.py            # 查看当前应用统计
python get_usage_by_time.py    # 查看时间段分布
python check_cpu.py            # 检查 CPU 占用
```

## 配置说明

### config.json

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| interval_minutes | int | 60 | 定时采集间隔（分钟） |
| top_processes | int | 50 | 每次采集保留的进程数量 |
| exclude_system | bool | true | 是否排除系统进程 |
| storage_backend | str | "sqlite" | 存储后端（"sqlite" 或 "json"） |
| foreground_interval_seconds | float | 1 | 前台检测采样间隔（秒） |
| tray_enabled | bool | true | 是否启用系统托盘 |
| tray_refresh_seconds | int | 60 | 托盘 tooltip 刷新间隔（秒） |
| web_host | str | "127.0.0.1" | Web 仪表盘监听地址 |
| web_port | int | 8080 | Web 仪表盘端口 |
| fragment_time_threshold_minutes | int | 5 | 碎片时间阈值（分钟） |
| app_categories | object | {...} | 应用分类规则映射 |
| focus_apps | array | [...] | 专注力追踪的目标应用列表 |

### V2 配置文件（首次使用对应功能时自动创建）

| 文件 | 说明 |
|------|------|
| config/usage_goals.json | 使用目标配置（goals 命令） |
| config/projects.json | 项目名称→路径映射（projects 命令） |
| config/break_rules.json | 休息提醒规则（break 命令） |
| config/sync_config.json | 同步配置：远程路径、设备名（sync 命令） |
| config/timeout_alerts.json | 超时提醒阈值配置（timeout 命令） |

## 数据存储

V2 默认使用 SQLite 数据库 (`data/usage_tracker.db`)，包含以下表：

| 表名 | 说明 |
|------|------|
| usage_records | 使用记录（V1 字段 + is_foreground、foreground_minutes、device_id） |
| foreground_sessions | 前台窗口会话 |
| focus_sessions | 专注会话 |
| context_switches | 应用切换事件 |
| project_sessions | 项目级会话 |

通过 `config.json` 的 `storage_backend` 可切换回 JSON 模式（`"json"`），保持 V1 兼容。

## 常见问题

**Q: 如何从 V1 升级到 V2？**
A: 运行 `python app_usage_tracker.py migrate` 将 JSON 数据导入 SQLite。V1 命令全部兼容。

**Q: pywin32 未安装怎么办？**
A: 前台检测功能会自动降级，其他功能正常使用。建议通过 `pip install -r requirements.txt` 一键安装全部依赖。

**Q: Web 仪表盘打不开？**
A: 确保已安装 Flask（`pip install -r requirements.txt` 已包含）。

**Q: 系统托盘图标不显示？**
A: 确保已安装 pystray 和 Pillow（`pip install -r requirements.txt` 已包含）。

**Q: 如何配置多设备同步？**
A: 首次执行 `python app_usage_tracker.py sync --push` 会自动创建 `config/sync_config.json`，编辑其中的 `remote_path` 为共享文件夹路径或 S3 URI。

**Q: 如何使用 S3 同步？**
A: 编辑 `requirements.txt` 取消 `boto3` 注释，运行 `pip install -r requirements.txt`，然后在 `config/sync_config.json` 中设置 S3 URI。

## 技术栈

- Python 3.8+ (标准库: sqlite3, json, threading, pathlib, csv, argparse)
- psutil — 进程信息获取
- pywin32 — 前台窗口检测（可选，缺失时降级）
- Flask + Jinja2 — Web 仪表盘（可选）
- ECharts (CDN) — 浏览器端交互式图表
- pystray + Pillow — 系统托盘（可选）
- matplotlib — 静态可视化图表（可选）
- boto3 — S3 同步（可选）

## 许可证

版权所有 © 2026 [KK-Irving](https://github.com/KK-Irving)

本项目采用 [MIT 许可证](LICENSE) 开源。
