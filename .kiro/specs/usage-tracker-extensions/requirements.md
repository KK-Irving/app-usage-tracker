# 需求文档：应用使用追踪器功能扩展

## 简介

本文档定义了对现有 App Usage Tracker（应用使用时间追踪工具）的功能扩展需求。现有系统已具备基础的进程数据采集（`get_usage.py`、`scripts/collect_usage.py`）、应用分类（`app_categories.py`）、时间段分析（`get_usage_by_time.py`）、每日报告（`scripts/get_daily_report.py`）、专注力追踪（`scripts/focus_tracker.py`）、碎片时间分析（`scripts/fragment_analyzer.py`）、超时提醒（`scripts/timeout_alert.py`）、周报/月报（`scripts/analyze_trends.py`）以及数据导出（`scripts/export_data.py`）等功能的初步实现。

本次扩展的目标是：修复现有代码中的缺陷，增强各模块的健壮性和可用性，并补充缺失的功能（如可视化图表），使整个工具链达到可靠、可用的生产质量。

## 术语表

- **Tracker**：App Usage Tracker 系统整体，即本项目的应用使用时间追踪工具
- **Collector**：数据采集模块，负责通过 psutil 获取进程信息并持久化到 JSON 文件
- **Classifier**：应用分类模块，负责将进程名称映射到预定义的分类标签（工作/社交/娱乐/开发/系统/其他）
- **Reporter**：报告生成模块，负责生成每日报告、周报、月报
- **FocusTracker**：专注力追踪模块，负责检测深度工作时段并计算专注度分数
- **FragmentAnalyzer**：碎片时间分析模块，负责识别短时间使用并统计碎片化程度
- **TimeoutMonitor**：超时提醒模块，负责监控应用使用时长并在超过阈值时发送通知
- **Exporter**：数据导出模块，负责将采集数据导出为 CSV 格式
- **Visualizer**：可视化模块，负责使用 matplotlib 生成图表
- **Scheduler**：定时调度模块，负责按计划执行数据采集任务
- **Category_Config**：应用分类配置，存储在 `config/app_categories.json` 中的分类规则
- **Usage_Record**：单条使用记录，包含 timestamp、hour、Name、Category、CPU、MemoryMB、DurationMinutes 字段
- **Focus_Session**：一段连续使用工作/开发类应用的时间段，时长不低于指定阈值
- **Fragment**：碎片时间，指使用时长低于配置阈值（默认 5 分钟）的应用会话

## 需求

### 需求 1：修复现有代码缺陷

**用户故事：** 作为开发者，我希望现有代码中的语法错误和逻辑缺陷被修复，以便所有模块可以正常运行。

#### 验收标准

1. WHEN `scripts/get_daily_report.py` 被执行, THE Reporter SHALL 无语法错误地完成运行（修复第 248 行的赋值语句在 if 条件中的语法错误）
2. WHEN `scripts/export_data.py` 的 `export_monthly_csv` 函数被调用, THE Exporter SHALL 无语法错误地完成运行（修复字典字面量中缺少的右括号）
3. WHEN `config/app_categories.json` 被加载, THE Classifier SHALL 成功解析为合法的 JSON 对象（移除文件头部的 Python 注释行）
4. WHEN `scripts/fragment_analyzer.py` 导入 `app_categories` 模块, THE FragmentAnalyzer SHALL 使用正确的模块路径完成导入（当前使用 `app_usage_tracker.app_categories` 路径不正确）
5. WHEN `scripts/focus_tracker.py` 导入 `app_categories` 模块, THE FocusTracker SHALL 使用正确的模块路径完成导入

### 需求 2：增强应用分类标签系统

**用户故事：** 作为用户，我希望应用分类系统更加准确和灵活，以便自动区分"工作/社交/娱乐"等应用类别。

#### 验收标准

1. THE Classifier SHALL 提供统一的分类接口，使所有模块（Collector、Reporter、FocusTracker、FragmentAnalyzer）使用同一套分类逻辑
2. WHEN 一个进程名称匹配多个分类的关键词时, THE Classifier SHALL 按照优先级顺序返回第一个匹配的分类（优先级：开发 > 工作 > 社交 > 娱乐 > 系统 > 其他）
3. WHEN 用户通过命令行添加新的分类规则时, THE Classifier SHALL 将规则持久化到 `config/app_categories.json` 并立即生效
4. THE Category_Config SHALL 使用合法的 JSON 格式存储，包含分类名称、颜色图标和应用关键词列表
5. WHEN 一个进程名称未匹配任何分类规则时, THE Classifier SHALL 返回"其他"分类

### 需求 3：增强定时采集与调度

**用户故事：** 作为用户，我希望数据采集可以按计划自动执行，以便无需手动运行即可持续记录使用情况。

#### 验收标准

1. THE Scheduler SHALL 支持通过 Windows 任务计划程序（Task Scheduler）设置定时采集任务
2. WHEN 定时采集任务执行时, THE Collector SHALL 将采集到的 Usage_Record 追加到当日的 JSON 数据文件中
3. WHEN 数据文件路径不存在时, THE Collector SHALL 自动创建所需的目录结构
4. THE Collector SHALL 在 `config.json` 中读取 `interval_minutes`、`top_processes`、`exclude_system` 配置项
5. WHEN `exclude_system` 配置为 true 时, THE Collector SHALL 过滤掉分类为"系统"的进程记录

### 需求 4：增强每日报告生成

**用户故事：** 作为用户，我希望每日报告包含完整的使用汇总，以便了解当天的时间分配情况。

#### 验收标准

1. WHEN 用户请求生成每日报告时, THE Reporter SHALL 输出包含以下部分的报告：总览、分类汇总、Top 10 应用、时间块分布、专注力分析、碎片时间分析、空闲时间检测、建议
2. WHEN 指定日期参数时, THE Reporter SHALL 加载对应日期的数据文件生成报告
3. WHEN 指定日期无数据文件时, THE Reporter SHALL 输出明确的错误提示信息
4. THE Reporter SHALL 将生成的报告同时输出到控制台和保存到 `data/reports/daily_YYYY-MM-DD.md` 文件
5. THE Reporter SHALL 在建议部分基于工作时间占比和专注时长给出具体的改进建议

### 需求 5：增强时间块分析

**用户故事：** 作为用户，我希望系统自动识别高效时段和低效时段，以便优化时间安排。

#### 验收标准

1. THE Reporter SHALL 将一天划分为 7 个时间块：深夜(0-6)、早上(6-9)、上午(9-12)、午间(12-14)、下午(14-18)、傍晚(18-21)、晚上(21-24)
2. WHEN 分析时间块时, THE Reporter SHALL 为每个时间块统计活跃记录数、总使用时长和 Top 3 应用
3. WHEN 某时间块的工作/开发类应用占比超过 60% 时, THE Reporter SHALL 将该时间块标记为"高效时段"
4. WHEN 某时间块的社交/娱乐类应用占比超过 50% 时, THE Reporter SHALL 将该时间块标记为"低效时段"
5. THE Reporter SHALL 在报告中以可视化进度条展示各时间块的使用占比

### 需求 6：增强超时提醒功能

**用户故事：** 作为用户，我希望在某个应用使用时间过长时收到通知，以便控制使用时间。

#### 验收标准

1. THE TimeoutMonitor SHALL 从 `config/timeout_alerts.json` 加载每个应用的超时阈值配置
2. WHEN 配置文件不存在时, THE TimeoutMonitor SHALL 使用内置的默认阈值配置
3. WHEN 某应用的运行时长超过配置的阈值时, THE TimeoutMonitor SHALL 通过 Windows Toast 通知发送提醒
4. THE TimeoutMonitor SHALL 对同一应用在同一天内仅发送一次超时通知，避免重复打扰
5. WHEN 用户通过命令行添加或移除告警规则时, THE TimeoutMonitor SHALL 将变更持久化到配置文件
6. WHEN 用户执行 `--check` 命令时, THE TimeoutMonitor SHALL 立即检查所有应用并输出当前超时状态

### 需求 7：增强专注力追踪功能

**用户故事：** 作为用户，我希望系统记录深度工作时长并生成专注力报告，以便了解自己的专注模式。

#### 验收标准

1. THE FocusTracker SHALL 基于连续使用工作/开发类应用的时长检测 Focus_Session
2. WHEN 连续使用工作/开发类应用的时长达到 25 分钟（可配置）时, THE FocusTracker SHALL 将该时段记录为一个 Focus_Session
3. THE FocusTracker SHALL 计算专注度分数（0-100），公式为：工作/开发类应用时长占总时长的百分比
4. WHEN 专注度分数 >= 80 时, THE FocusTracker SHALL 标记为"高度专注"；60-79 为"较为专注"；40-59 为"注意力分散"；< 40 为"休闲模式"
5. THE FocusTracker SHALL 支持番茄钟计时模式，默认 25 分钟一个周期，计时结束后记录到 `data/focus_sessions.json`
6. THE FocusTracker SHALL 在专注力报告中按分类展示使用时长占比和可视化进度条

### 需求 8：增强碎片时间分析功能

**用户故事：** 作为用户，我希望系统自动识别碎片时间并统计浪费情况，以便减少无效切换。

#### 验收标准

1. THE FragmentAnalyzer SHALL 将使用时长低于 `config.json` 中 `fragment_time_threshold_minutes`（默认 5 分钟）的会话标记为 Fragment
2. THE FragmentAnalyzer SHALL 计算碎片化指数，公式为：活跃小时数 / 总记录数
3. THE FragmentAnalyzer SHALL 将碎片时间分为三级：短碎片（< 10 分钟）、中碎片（10-30 分钟）、长使用（> 30 分钟）
4. THE FragmentAnalyzer SHALL 在报告中展示碎片时间的主要分布应用和出现次数
5. THE FragmentAnalyzer SHALL 基于碎片时间模式给出利用建议（如短碎片适合回复消息，中碎片适合编写文档）

### 需求 9：周报与月报生成

**用户故事：** 作为用户，我希望每周/每月自动生成使用趋势报告，以便与上一周期对比效率变化。

#### 验收标准

1. WHEN 用户请求生成周报时, THE Reporter SHALL 聚合本周 7 天的数据并与上周数据进行对比
2. WHEN 用户请求生成月报时, THE Reporter SHALL 聚合本月所有天的数据并与上月数据进行对比
3. THE Reporter SHALL 在周报/月报中展示数据量变化百分比和 Top 5 应用排名变化
4. THE Reporter SHALL 将周报保存到 `data/reports/weekly_YYYY-MM-DD.md`，月报保存到 `data/reports/monthly_YYYY-MM-DD.md`
5. WHEN 对比周期无数据时, THE Reporter SHALL 输出明确提示并仅展示当前周期的数据

### 需求 10：数据导出功能增强

**用户故事：** 作为用户，我希望将采集数据导出为 CSV 格式，以便在 Excel 中进行自定义分析。

#### 验收标准

1. WHEN 用户执行单日导出时, THE Exporter SHALL 将指定日期的所有 Usage_Record 导出为 CSV 文件，包含 timestamp、hour、Name、Category、CPU、MemoryMB、DurationMinutes 字段
2. WHEN 用户执行周导出时, THE Exporter SHALL 聚合本周 7 天的数据导出为单个 CSV 文件
3. WHEN 用户执行月导出时, THE Exporter SHALL 聚合本月所有天的数据导出为单个 CSV 文件
4. THE Exporter SHALL 使用 `utf-8-sig` 编码写入 CSV 文件，确保 Excel 正确显示中文字符
5. WHEN 指定日期无数据时, THE Exporter SHALL 输出明确的错误提示信息

### 需求 11：可视化图表生成

**用户故事：** 作为用户，我希望生成可视化图表，以便直观了解应用使用分布和时间趋势。

#### 验收标准

1. THE Visualizer SHALL 使用 matplotlib 生成分类使用时长的饼图
2. THE Visualizer SHALL 使用 matplotlib 生成每小时活跃度的柱状图
3. THE Visualizer SHALL 使用 matplotlib 生成周趋势折线图（每日总使用时长变化）
4. THE Visualizer SHALL 将生成的图表保存为 PNG 文件到 `data/reports/charts/` 目录
5. THE Visualizer SHALL 在图表中正确显示中文字体（配置 matplotlib 使用系统中文字体）
6. WHEN 数据不足以生成图表时, THE Visualizer SHALL 输出明确的提示信息而非抛出异常

### 需求 12：统一命令行入口

**用户故事：** 作为用户，我希望通过统一的命令行入口访问所有功能，以便简化操作流程。

#### 验收标准

1. THE Tracker SHALL 通过 `python app_usage_tracker.py <命令>` 提供统一的命令行入口
2. THE Tracker SHALL 支持以下命令：collect、daily、weekly、monthly、focus、fragments、export、categories、timeout、chart、help
3. WHEN 用户输入未知命令时, THE Tracker SHALL 输出帮助信息并列出所有可用命令
4. WHEN 用户不带参数运行时, THE Tracker SHALL 输出帮助信息
5. THE Tracker SHALL 确保所有子模块的导入路径正确，无论从项目根目录还是 scripts 目录执行
