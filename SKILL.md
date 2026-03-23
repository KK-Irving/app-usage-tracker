---
name: app-usage-tracker
description: |
  Windows 应用使用时间追踪器（V2）。用于：
  (1) 自动采集进程数据，统计各应用使用时长、CPU、内存
  (2) 智能分类应用（开发/工作/社交/娱乐/系统/其他）
  (3) 前台窗口检测，区分前台活跃和后台运行
  (4) 生成每日/周/月多维度分析报告
  (5) 目标设定与达成率追踪
  (6) 应用切换频率分析与上下文切换成本
  (7) Web 仪表盘（Flask + ECharts 交互式图表）
  (8) 多设备数据同步（本地文件夹/S3）
  (9) 项目级时间追踪（VS Code 窗口标题解析）
  (10) 智能建议引擎（基于 7 天历史数据）
  (11) 休息提醒（20-20-20 法则 + 长休息）
  (12) SQLite 数据库后端（支持 JSON 回退）
  (13) 系统托盘常驻（pystray 实时显示）
  触发场景：用户说"统计应用使用时间"、"查看今天用了哪些应用"、"分析我的时间分布"、"应用使用报告"、"设定使用目标"、"启动 Web 仪表盘"、"启动系统托盘"等
---

# App Usage Tracker V2

基于 Python 的 Windows 应用使用时间追踪工具，自动采集进程数据，智能分类，生成多维度分析报告。

## 安装

```bash
pip install -r requirements.txt
```

`requirements.txt` 包含所有功能依赖（psutil、pywin32、flask、pystray、Pillow、matplotlib）。S3 同步需取消注释 boto3。

## 统一命令行入口

所有功能通过 `python app_usage_tracker.py <命令>` 访问。

### V1 命令

| 命令 | 说明 |
|------|------|
| collect | 采集当前应用数据 |
| daily | 生成每日报告（--date 指定日期） |
| weekly | 生成周报 |
| monthly | 生成月报 |
| focus | 专注力分析/番茄钟（--timer 分钟数） |
| fragments | 碎片时间分析 |
| export | 数据导出 CSV（--weekly / --monthly） |
| categories | 管理应用分类（add/remove/list） |
| timeout | 超时提醒（--check / --add / --remove） |
| chart | 可视化图表（--pie / --bar / --line） |
| schedule | Windows 定时任务管理（--setup-all） |

### V2 新增命令

| 命令 | 说明 |
|------|------|
| goals | 目标管理（--add 分类 min/max 分钟 / --list / --evaluate / --remove） |
| switches | 切换分析（--date 指定日期） |
| projects | 项目管理（--add 名称 路径 / --list / --report / --remove） |
| web | 启动 Web 仪表盘（默认 127.0.0.1:8080） |
| sync | 多设备同步（--push / --pull / --report） |
| break | 休息提醒（--start / --list / --add 阈值 休息 消息） |
| tray | 启动系统托盘常驻 |
| migrate | JSON→SQLite 数据迁移（--dry-run 预览） |

## 独立工具脚本

| 脚本 | 说明 |
|------|------|
| `get_usage.py` | 即时统计当前应用使用情况 |
| `get_usage_by_time.py` | 按时间段分析应用分布 |
| `check_cpu.py` | 快速检查 CPU 占用 |

## 项目结构

```
app-usage-tracker/
├── app_usage_tracker.py          # 统一命令行入口
├── app_categories.py             # 统一分类引擎
├── config.json                   # 全局配置
├── requirements.txt              # pip 依赖清单
├── check_cpu.py                  # CPU 检查工具
├── get_usage.py                  # 即时应用统计
├── get_usage_by_time.py          # 时间段分布
├── config/
│   ├── app_categories.json       # 应用分类规则
│   ├── timeout_alerts.json       # 超时提醒配置（自动创建）
│   ├── usage_goals.json          # 目标配置（自动创建）
│   ├── projects.json             # 项目映射（自动创建）
│   ├── break_rules.json          # 休息规则（自动创建）
│   └── sync_config.json          # 同步配置（自动创建）
├── scripts/
│   ├── collect_usage.py          # 数据采集
│   ├── collect_usage_v2.py       # V2 独立采集脚本
│   ├── get_daily_report.py       # 每日报告
│   ├── analyze_trends.py         # 周报/月报
│   ├── focus_tracker.py          # 专注力追踪
│   ├── fragment_analyzer.py      # 碎片时间分析
│   ├── timeout_alert.py          # 超时提醒
│   ├── export_data.py            # CSV 导出
│   ├── visualizer.py             # 可视化图表
│   ├── scheduler.py              # 定时任务调度
│   ├── data_store.py             # 统一数据访问层（SQLite/JSON）
│   ├── db_migrate.py             # JSON→SQLite 迁移
│   ├── foreground_detector.py    # 前台窗口检测
│   ├── goal_manager.py           # 目标管理
│   ├── switch_analyzer.py        # 切换分析
│   ├── project_tracker.py        # 项目追踪
│   ├── suggestion_engine.py      # 智能建议
│   ├── break_reminder.py         # 休息提醒
│   ├── sync_manager.py           # 多设备同步
│   ├── web_dashboard.py          # Web 仪表盘
│   └── tray_app.py               # 系统托盘
├── templates/
│   ├── base.html                 # 基础布局
│   ├── dashboard.html            # 首页仪表盘
│   └── goals.html                # 目标达成率页面
├── data/
│   ├── usage_tracker.db          # SQLite 数据库
│   └── reports/                  # 报告和图表
├── tests/
│   └── test_db_migrate.py        # 迁移工具测试
├── LICENSE                       # MIT 许可证
└── README.md                     # 项目说明
```

## 配置

### config.json 主要配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| interval_minutes | 60 | 采集间隔（分钟） |
| top_processes | 50 | 保留进程数量 |
| exclude_system | true | 排除系统进程 |
| storage_backend | "sqlite" | 存储后端（sqlite/json） |
| foreground_interval_seconds | 1 | 前台检测采样间隔（秒） |
| tray_enabled | true | 启用系统托盘 |
| tray_refresh_seconds | 60 | 托盘刷新间隔（秒） |
| web_host | "127.0.0.1" | Web 仪表盘地址 |
| web_port | 8080 | Web 仪表盘端口 |
| fragment_time_threshold_minutes | 5 | 碎片时间阈值（分钟） |
| app_categories | {...} | 应用分类规则 |
| focus_apps | [...] | 专注力目标应用 |

## 数据存储

默认使用 SQLite (`data/usage_tracker.db`)，包含表：usage_records、foreground_sessions、focus_sessions、context_switches、project_sessions。

可通过 `config.json` 的 `storage_backend: "json"` 切换回 V1 JSON 文件模式。

## 技术栈

- Python 3.8+（标准库: sqlite3, json, threading, pathlib, csv, argparse）
- psutil — 进程信息获取
- pywin32 — 前台窗口检测（可选，缺失时降级）
- Flask + Jinja2 — Web 仪表盘（可选）
- ECharts (CDN) — 交互式图表
- pystray + Pillow — 系统托盘（可选）
- matplotlib — 静态图表（可选）
- boto3 — S3 同步（可选）
