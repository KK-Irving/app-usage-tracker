# 📱 App Usage Tracker — 应用使用时间追踪器

一个基于 Python 的 Windows 应用使用时间追踪工具。自动采集进程数据，智能分类应用，生成多维度分析报告，帮助你了解时间去向、提升工作效率。

## 功能概览

| 功能 | 说明 |
|------|------|
| 🔄 数据采集 | 通过 psutil 获取进程信息，记录应用名称、CPU、内存、运行时长 |
| 🏷️ 智能分类 | 自动将应用归类为 开发/工作/社交/娱乐/系统/其他，支持自定义规则 |
| 📊 每日报告 | 包含总览、分类汇总、Top 10 应用、时间块分布、专注力、碎片时间、建议等 8 个部分 |
| 📈 周报/月报 | 聚合多日数据，与上周/上月对比，展示趋势变化和 Top 5 应用排名 |
| 🎯 专注力追踪 | 检测深度工作时段，计算专注度分数（0-100），支持番茄钟计时 |
| ⏱️ 碎片时间分析 | 识别短时间使用，三级分类（短碎片/中碎片/长使用），给出利用建议 |
| ⏰ 超时提醒 | 应用使用超过阈值时发送 Windows Toast 通知，同一天同一应用仅提醒一次 |
| 📤 数据导出 | 导出 CSV（utf-8-sig 编码），支持单日/周/月导出，Excel 友好 |
| 📉 可视化图表 | 使用 matplotlib 生成分类饼图、每小时活跃度柱状图、周趋势折线图 |
| ⏲️ 定时任务 | 通过 Windows 任务计划程序自动执行采集、生成报告、导出数据 |

## 环境要求

- Python 3.8+
- Windows 操作系统
- 依赖库：
  - `psutil` — 进程数据采集（必需）
  - `matplotlib` — 可视化图表（可选，仅 `chart` 命令需要）

```bash
pip install psutil matplotlib
```

## 快速开始

```bash
# 1. 采集一次数据
python app_usage_tracker.py collect

# 2. 生成今日报告
python app_usage_tracker.py daily

# 3. 一键设置所有定时任务（采集 + 报告 + 导出）
python app_usage_tracker.py schedule --setup-all
```

## 项目结构

```
app-usage-tracker/
├── app_usage_tracker.py          # 统一命令行入口
├── app_categories.py             # 统一分类引擎
├── get_usage.py                  # 即时查看当前应用使用统计
├── get_usage_by_time.py          # 即时查看时间段分布
├── check_cpu.py                  # CPU 占用检查
├── config.json                   # 全局配置
├── config/
│   ├── app_categories.json       # 应用分类规则
│   └── timeout_alerts.json       # 超时提醒配置（自动生成）
├── scripts/
│   ├── collect_usage.py          # 数据采集模块
│   ├── collect_usage_v2.py       # 采集模块（旧版）
│   ├── get_daily_report.py       # 每日报告生成
│   ├── analyze_trends.py         # 周报/月报生成
│   ├── focus_tracker.py          # 专注力追踪
│   ├── fragment_analyzer.py      # 碎片时间分析
│   ├── timeout_alert.py          # 超时提醒
│   ├── export_data.py            # CSV 数据导出
│   ├── visualizer.py             # 可视化图表（matplotlib）
│   └── scheduler.py              # 定时任务调度
├── data/                         # 数据目录（自动创建）
│   ├── usage_YYYY-MM-DD.json     # 每日采集数据
│   ├── focus_sessions.json       # 专注会话记录
│   ├── export_*.csv              # 导出的 CSV 文件
│   └── reports/
│       ├── daily_YYYY-MM-DD.md   # 每日报告
│       ├── weekly_YYYY-MM-DD.md  # 周报
│       ├── monthly_YYYY-MM-DD.md # 月报
│       └── charts/               # 可视化图表 PNG
└── SKILL.md                      # Skill 元数据
```

## 命令详解

所有功能通过统一入口 `python app_usage_tracker.py <命令>` 访问。

### 🔄 collect — 数据采集

采集当前系统中所有运行进程的使用数据，追加到当日的 JSON 数据文件中。

```bash
python app_usage_tracker.py collect
```

采集的字段：
- `timestamp` — 采集时间
- `hour` — 小时 (0-23)
- `Name` — 进程名称
- `Category` — 分类标签（由统一分类引擎自动判定）
- `CPU` — CPU 使用率 (%)
- `MemoryMB` — 内存使用量 (MB)
- `DurationMinutes` — 运行时长（分钟）

行为说明：
- 从 `config.json` 读取 `top_processes`（默认 50）控制保留的进程数量
- 当 `exclude_system` 为 `true` 时，自动过滤系统进程
- 数据目录不存在时自动创建

---

### 📊 daily — 每日报告

生成包含 8 个部分的完整每日报告。

```bash
# 生成今日报告
python app_usage_tracker.py daily

# 生成指定日期的报告
python app_usage_tracker.py daily --date 2026-03-19
```

报告包含的 8 个部分：

1. **总览** — 总使用时长、记录总数、应用数量
2. **分类汇总** — 各分类的使用时长占比（含可视化进度条）
3. **Top 10 应用** — 按使用时长排序的前 10 个应用
4. **时间块分布** — 将一天划分为 7 个时间块，标记高效/低效时段
   - 🌙 深夜 (0-6) / 🌅 早上 (6-9) / ☀️ 上午 (9-12) / 🍚 午间 (12-14)
   - 🌤️ 下午 (14-18) / 🌆 傍晚 (18-21) / 🌃 晚上 (21-24)
   - 🟢 高效时段：工作/开发类应用占比 > 60%
   - 🔴 低效时段：社交/娱乐类应用占比 > 50%
5. **专注力分析** — 连续使用工作/开发类应用 ≥ 30 分钟的时段
6. **碎片时间分析** — 使用时长 ≤ 10 分钟的碎片记录统计
7. **空闲时间检测** — 低活跃时段识别
8. **建议** — 基于工作时间占比和专注时长给出改进建议

报告同时输出到控制台和保存到 `data/reports/daily_YYYY-MM-DD.md`。

---

### 📈 weekly / monthly — 周报与月报

```bash
# 生成周报（本周 vs 上周）
python app_usage_tracker.py weekly

# 生成月报（本月 vs 上月）
python app_usage_tracker.py monthly
```

报告内容：
- 数据量变化百分比
- Top 5 应用排名及与上一周期的对比
- 无对比数据时仅展示当前周期

保存位置：
- 周报：`data/reports/weekly_YYYY-MM-DD.md`
- 月报：`data/reports/monthly_YYYY-MM-DD.md`

---

### 🎯 focus — 专注力追踪

```bash
# 分析今日专注力
python app_usage_tracker.py focus

# 分析指定日期
python app_usage_tracker.py focus --date 2026-03-19

# 启动番茄钟计时（25 分钟）
python app_usage_tracker.py focus --timer 25

# 自定义计时时长（45 分钟）
python app_usage_tracker.py focus --timer 45
```

专注度分数（0-100）= 工作/开发类应用时长 ÷ 总时长 × 100

| 分数 | 状态 |
|------|------|
| ≥ 80 | 🔥 高度专注 |
| 60-79 | ⚡ 较为专注 |
| 40-59 | ⚠️ 注意力分散 |
| < 40 | 😴 休闲模式 |

番茄钟计时结束后自动记录到 `data/focus_sessions.json`。中途取消（Ctrl+C）如果已专注 ≥ 5 分钟也会记录。

---

### ⏱️ fragments — 碎片时间分析

```bash
python app_usage_tracker.py fragments
```

分析内容：
- **碎片化指数** = 活跃小时数 ÷ 总记录数
- **三级分类**：
  - ⚡ 短碎片：< 10 分钟（适合回复消息、查看邮件）
  - ⏰ 中碎片：10-30 分钟（适合编写文档、处理工单）
  - 🔵 长使用：> 30 分钟
- **利用建议**：基于碎片时间模式推荐适合的任务

---

### ⏰ timeout — 超时提醒

```bash
# 立即检查所有应用是否超时
python app_usage_tracker.py timeout --check

# 查看当前告警配置
python app_usage_tracker.py timeout --list

# 添加告警规则（应用名 阈值分钟）
python app_usage_tracker.py timeout --add 抖音 30

# 移除告警规则
python app_usage_tracker.py timeout --remove 抖音

# 启动持续监控模式（每 5 分钟检查一次）
python app_usage_tracker.py timeout --monitor
python app_usage_tracker.py timeout --monitor --interval 600  # 每 10 分钟
```

特性：
- 超时时通过 Windows Toast 通知提醒
- 同一应用同一天仅发送一次通知，避免重复打扰
- 配置文件不存在时使用内置默认阈值
- 规则持久化到 `config/timeout_alerts.json`

默认告警规则：

| 应用 | 阈值 |
|------|------|
| Chrome | 120 分钟 |
| 微信/WeChat | 60 分钟 |
| 钉钉/DingTalk | 120 分钟 |
| QQ | 60 分钟 |
| 抖音 | 30 分钟 |
| bilibili | 60 分钟 |
| 小红书 | 30 分钟 |

---

### 📤 export — 数据导出

```bash
# 导出今日数据
python app_usage_tracker.py export

# 导出指定日期
python app_usage_tracker.py export --daily 2026-03-19

# 导出本周数据
python app_usage_tracker.py export --weekly

# 导出本月数据
python app_usage_tracker.py export --monthly
```

导出格式：CSV（utf-8-sig 编码，Excel 可直接打开显示中文）

CSV 字段：`timestamp`, `hour`, `Name`, `Category`, `CPU`, `MemoryMB`, `DurationMinutes`

导出位置：`data/export_*.csv`

---

### 🏷️ categories — 应用分类管理

```bash
# 查看当前分类配置
python app_usage_tracker.py categories

# 添加应用到分类
python app_usage_tracker.py categories add 工作 notion

# 从分类中移除应用
python app_usage_tracker.py categories remove 娱乐 bilibili

# 重置为默认分类
python app_usage_tracker.py categories reset
```

分类优先级（从高到低）：开发 > 工作 > 社交 > 娱乐 > 系统 > 其他

当一个进程名称匹配多个分类时，返回优先级最高的分类。未匹配任何规则的应用归为"其他"。

预置分类：

| 分类 | 图标 | 包含应用示例 |
|------|------|-------------|
| 开发 | 🟣 | python, java, node, git, docker, pycharm, webstorm |
| 工作 | 🔵 | chrome, msedge, vscode, powershell, 钉钉, 飞书, outlook, teams |
| 社交 | 🟡 | 微信, QQ, Telegram, Discord, WhatsApp |
| 娱乐 | 🔴 | Spotify, 网易云音乐, Steam, bilibili, PotPlayer |
| 系统 | ⚪ | explorer, System, svchost, RuntimeBroker |

分类规则存储在 `config/app_categories.json`，修改后立即生效。

---

### 📉 chart — 可视化图表

需要安装 matplotlib：`pip install matplotlib`

```bash
# 生成所有图表（饼图 + 柱状图 + 趋势图）
python app_usage_tracker.py chart

# 指定日期
python app_usage_tracker.py chart --date 2026-03-19

# 仅生成分类饼图
python app_usage_tracker.py chart --pie

# 仅生成每小时活跃度柱状图
python app_usage_tracker.py chart --bar

# 仅生成周趋势折线图
python app_usage_tracker.py chart --trend
```

图表类型：
- **分类饼图** — 各分类使用时长占比
- **每小时活跃度柱状图** — 24 小时活跃记录分布，高峰时段高亮显示
- **周趋势折线图** — 本周每日总使用时长变化

图表保存为 PNG 到 `data/reports/charts/` 目录。自动配置中文字体（SimHei / Microsoft YaHei）。

---

### ⏲️ schedule — 定时任务管理

通过 Windows 任务计划程序（Task Scheduler）管理自动化任务。

```bash
# 一键设置所有定时任务（推荐）
python app_usage_tracker.py schedule --setup-all

# 仅设置定时采集（按 config.json 中 interval_minutes 间隔）
python app_usage_tracker.py schedule --setup

# 设置每日自动生成报告（默认 23:00）
python app_usage_tracker.py schedule --setup-report

# 设置每日自动导出 CSV（默认 23:30）
python app_usage_tracker.py schedule --setup-export

# 自定义执行时间
python app_usage_tracker.py schedule --setup-report --time 22:00

# 查看当前任务状态
python app_usage_tracker.py schedule --list

# 移除所有定时任务
python app_usage_tracker.py schedule --remove
```

注册的计划任务：

| 任务名 | 说明 | 默认时间 |
|--------|------|----------|
| AppUsageTracker_Collect | 定时数据采集 | 每 60 分钟 |
| AppUsageTracker_DailyReport | 每日报告生成 | 每天 23:00 |
| AppUsageTracker_DailyExport | 每日 CSV 导出 | 每天 23:30 |

> 💡 设置计划任务可能需要管理员权限。

---

### ❓ help — 帮助

```bash
python app_usage_tracker.py help
```

输入未知命令或不带参数运行时也会显示帮助信息。

## 配置说明

### config.json — 全局配置

```json
{
  "interval_minutes": 60,
  "top_processes": 50,
  "exclude_system": true,
  "fragment_time_threshold_minutes": 5,
  "focus_threshold_minutes": 25
}
```

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `interval_minutes` | int | 60 | 定时采集间隔（分钟） |
| `top_processes` | int | 50 | 每次采集保留的进程数量 |
| `exclude_system` | bool | true | 是否排除系统进程 |
| `fragment_time_threshold_minutes` | int | 5 | 碎片时间阈值（分钟） |
| `focus_threshold_minutes` | int | 25 | 专注会话最低时长（分钟） |

### config/app_categories.json — 分类规则

```json
{
  "开发": {
    "color": "🟣",
    "apps": ["python", "java", "node", "git", "docker", "pycharm"]
  },
  "工作": {
    "color": "🔵",
    "apps": ["chrome", "vscode", "outlook", "teams", "钉钉"]
  }
}
```

匹配规则：进程名称（不区分大小写）包含 `apps` 列表中的任意关键词即匹配该分类。

### config/timeout_alerts.json — 超时提醒配置

```json
{
  "chrome": 120,
  "微信": 60,
  "抖音": 30
}
```

键为应用关键词，值为超时阈值（分钟）。

## 数据格式

### 每日数据文件 (data/usage_YYYY-MM-DD.json)

```json
{
  "date": "2026-03-20",
  "records": [
    {
      "timestamp": "2026-03-20 14:00:00",
      "hour": 14,
      "Name": "chrome.exe",
      "Category": "工作",
      "CPU": 2.5,
      "MemoryMB": 512.3,
      "DurationMinutes": 120.5
    }
  ]
}
```

### 专注会话 (data/focus_sessions.json)

```json
{
  "sessions": [
    {
      "date": "2026-03-20",
      "duration": 25,
      "timestamp": "2026-03-20T14:30:00"
    }
  ],
  "daily_stats": {}
}
```

## 示例输出

### 每日报告示例

```
======================================================================
📊 应用使用日报 - 2026年03月20日
======================================================================

🕐 总使用时长: 8h 32m
📝 记录总数: 156 条
📱 应用数量: 23 个

======================================================================
📈 分类使用情况
======================================================================
工作   ████████████████░░░░  78.2%  6h 40m (8个应用)
开发   ██░░░░░░░░░░░░░░░░░░  10.5%  0h 53m (3个应用)
社交   █░░░░░░░░░░░░░░░░░░░   6.1%  0h 31m (2个应用)
娱乐   ░░░░░░░░░░░░░░░░░░░░   3.2%  0h 16m (2个应用)
其他   ░░░░░░░░░░░░░░░░░░░░   2.0%  0h 10m (8个应用)

======================================================================
🕐 时间块分布
======================================================================

☀️ 上午 🟢 高效时段 (2h 45m)
  ████████████████████ 活跃记录: 42 | chrome.exe(15), Code.exe(12), python.exe(8)

🌤️ 下午 🟢 高效时段 (3h 10m)
  ██████████████████░░ 活跃记录: 38 | Code.exe(18), chrome.exe(10), git.exe(5)
```

## 常见问题

**Q: 采集数据需要管理员权限吗？**
A: 不需要。psutil 可以获取当前用户的进程信息。部分系统进程可能无法访问，会被自动跳过。

**Q: 图表中文显示为方块？**
A: 确保系统安装了 SimHei 或 Microsoft YaHei 字体。Windows 系统通常自带这些字体。

**Q: 定时任务设置失败？**
A: 以管理员权限运行命令提示符，再执行 `schedule --setup-all`。

**Q: 如何修改采集间隔？**
A: 编辑 `config.json` 中的 `interval_minutes`，然后重新执行 `schedule --setup`。

## 技术栈

- Python 3.8+
- psutil — 跨平台进程信息获取
- matplotlib — 数据可视化（可选）
- Windows Task Scheduler (schtasks) — 定时任务
- Windows Toast Notifications — 超时提醒通知
