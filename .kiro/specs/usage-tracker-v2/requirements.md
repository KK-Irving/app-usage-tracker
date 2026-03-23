# 需求文档：App Usage Tracker V2 — 十大扩展功能

## 简介

本文档定义了 App Usage Tracker V2 版本的十大全新扩展功能需求。现有系统（V1）已具备基于 psutil 的进程数据采集、应用分类、每日/周/月报告、专注力追踪、碎片时间分析、超时提醒、CSV 数据导出、matplotlib 可视化图表、Windows 定时任务调度等功能。

V2 版本的目标是在 V1 基础上进行重大升级，引入前台窗口检测、目标设定、应用切换分析、Web 仪表盘、多设备同步、项目级追踪、智能建议、休息提醒、SQLite 数据库后端、系统托盘常驻等十项新功能，全面提升追踪精度、数据管理能力和用户体验。

## 术语表

- **Tracker**：App Usage Tracker 系统整体
- **ForegroundDetector**：前台窗口检测模块，通过 Windows API（win32gui）检测当前前台活跃窗口
- **Foreground_Session**：一段前台活跃使用记录，包含应用名称、窗口标题、开始时间、结束时间、持续时长
- **GoalManager**：目标设定与达成率管理模块，负责定义、存储和评估每日使用目标
- **Usage_Goal**：一条使用目标规则，包含目标分类/应用、目标类型（上限/下限）、目标时长
- **SwitchAnalyzer**：应用切换频率分析模块，统计窗口切换次数并量化上下文切换成本
- **Context_Switch**：一次应用切换事件，记录从哪个应用切换到哪个应用及切换时间戳
- **WebDashboard**：Web 仪表盘模块，提供本地 Web 界面展示使用数据和交互式筛选
- **SyncManager**：多设备数据同步模块，负责将本地数据同步到云端并生成跨设备汇总报告
- **Device_Profile**：设备配置文件，包含设备唯一标识、设备名称、操作系统信息
- **ProjectTracker**：项目级时间追踪模块，将应用使用时间归属到具体项目
- **Project_Session**：一段项目级使用记录，包含项目名称、关联应用、工作区路径、持续时长
- **SuggestionEngine**：智能建议引擎，基于历史数据进行模式识别并生成个性化建议
- **Suggestion**：一条智能建议，包含建议类型、建议内容、置信度、关联数据
- **BreakReminder**：休息提醒模块，在连续工作一段时间后提醒用户休息
- **Break_Rule**：休息提醒规则，包含连续工作阈值、休息时长、提醒方式
- **DatabaseBackend**：SQLite 数据库后端模块，替代 JSON 文件存储，支持复杂查询
- **TrayApp**：系统托盘常驻模块，通过 pystray 在系统托盘显示图标和实时信息
- **Collector**：数据采集模块（V1 已有）
- **Classifier**：应用分类模块（V1 已有）
- **Reporter**：报告生成模块（V1 已有）
- **FocusTracker**：专注力追踪模块（V1 已有）
- **Usage_Record**：单条使用记录（V1 已有），包含 timestamp、hour、Name、Category、CPU、MemoryMB、DurationMinutes 字段
- **Category_Config**：应用分类配置（V1 已有），存储在 `config/app_categories.json`

## 需求

### 需求 1：前台应用追踪

**用户故事：** 作为用户，我希望系统能区分"前台活跃使用"和"后台挂着"的应用，以便报告中的使用时间更准确地反映实际操作行为。

#### 验收标准

1. THE ForegroundDetector SHALL 通过 win32gui.GetForegroundWindow() 和 win32gui.GetWindowText() 获取当前前台窗口的进程名称和窗口标题
2. WHEN ForegroundDetector 检测到前台窗口发生变化时, THE ForegroundDetector SHALL 记录一条 Foreground_Session，包含应用名称、窗口标题、开始时间和结束时间
3. THE ForegroundDetector SHALL 以可配置的采样间隔（默认 1 秒）轮询前台窗口状态
4. WHEN 采样间隔内前台窗口未发生变化时, THE ForegroundDetector SHALL 将该时间累加到当前 Foreground_Session 的持续时长中
5. THE Collector SHALL 在 Usage_Record 中新增 `is_foreground` 布尔字段和 `foreground_minutes` 浮点字段，区分前台活跃时间和后台运行时间
6. WHEN Reporter 生成每日报告时, THE Reporter SHALL 分别展示每个应用的前台活跃时间和后台运行时间
7. IF win32gui 模块不可用（如未安装 pywin32）, THEN THE ForegroundDetector SHALL 回退到仅使用 psutil 的模式并输出警告信息
8. THE ForegroundDetector SHALL 将 Foreground_Session 数据持久化到当日数据文件中，格式为 `foreground_sessions` 列表

### 需求 2：目标设定与达成率

**用户故事：** 作为用户，我希望设定每日使用目标（如"开发类 ≥ 4 小时"、"社交类 ≤ 1 小时"），以便在报告中看到目标达成率和趋势变化。

#### 验收标准

1. THE GoalManager SHALL 支持两种目标类型：下限目标（某分类/应用使用时间 ≥ 指定时长）和上限目标（某分类/应用使用时间 ≤ 指定时长）
2. WHEN 用户通过命令行设定目标时, THE GoalManager SHALL 将 Usage_Goal 持久化到 `config/usage_goals.json` 文件中
3. THE GoalManager SHALL 支持按分类名称（如"开发"、"社交"）或具体应用名称（如"chrome"）设定目标
4. WHEN Reporter 生成每日报告时, THE Reporter SHALL 计算每个 Usage_Goal 的达成率（实际时长 / 目标时长 × 100%）并在报告中展示
5. WHEN 下限目标的实际时长 ≥ 目标时长时, THE GoalManager SHALL 将该目标标记为"已达成"
6. WHEN 上限目标的实际时长 ≤ 目标时长时, THE GoalManager SHALL 将该目标标记为"已达成"
7. THE Reporter SHALL 在周报中展示过去 7 天每个目标的达成率趋势（达成天数 / 7）
8. WHEN 用户执行 `goals --list` 命令时, THE GoalManager SHALL 列出所有已配置的 Usage_Goal 及其当日达成状态
9. WHEN 用户执行 `goals --remove` 命令时, THE GoalManager SHALL 从配置文件中移除指定目标

### 需求 3：应用切换频率分析

**用户故事：** 作为用户，我希望了解每小时的应用切换次数和上下文切换成本，以便识别注意力分散的时段并改善专注力。

#### 验收标准

1. THE SwitchAnalyzer SHALL 基于 ForegroundDetector 的 Foreground_Session 数据统计每小时的应用切换次数
2. WHEN 前台窗口从应用 A 切换到应用 B 时, THE SwitchAnalyzer SHALL 记录一条 Context_Switch 事件，包含源应用、目标应用和切换时间戳
3. THE SwitchAnalyzer SHALL 计算每小时的平均切换次数，并标记切换频率异常高的时段（超过每小时平均值的 1.5 倍）
4. THE SwitchAnalyzer SHALL 计算"上下文切换成本"指标，公式为：切换次数 × 平均切换恢复时间（默认 2 分钟）
5. WHEN Reporter 生成每日报告时, THE Reporter SHALL 在专注力分析部分展示每小时切换次数分布和上下文切换成本总计
6. THE SwitchAnalyzer SHALL 识别最频繁的应用切换对（如 "VS Code ↔ Chrome"），并在报告中展示 Top 5 切换对
7. THE SwitchAnalyzer SHALL 将切换数据与 FocusTracker 的专注度分数关联，在报告中展示切换频率与专注度的相关性

### 需求 4：Web 仪表盘

**用户故事：** 作为用户，我希望通过本地 Web 界面查看使用数据，以便比命令行和 PNG 图表更直观地浏览和筛选数据。

#### 验收标准

1. THE WebDashboard SHALL 使用 Flask 或 FastAPI 框架提供本地 HTTP 服务，默认监听 `127.0.0.1:8080`
2. THE WebDashboard SHALL 提供首页仪表盘，展示今日使用概览（总时长、分类占比、Top 5 应用）
3. THE WebDashboard SHALL 提供交互式日期选择器，允许用户筛选指定日期范围的数据
4. THE WebDashboard SHALL 提供分类筛选功能，允许用户按分类（开发/工作/社交/娱乐/其他）过滤数据
5. THE WebDashboard SHALL 使用 JavaScript 图表库（如 Chart.js 或 ECharts）在浏览器端渲染交互式图表（饼图、柱状图、折线图）
6. THE WebDashboard SHALL 提供 RESTful API 端点，返回 JSON 格式的使用数据，供前端页面调用
7. WHEN 请求的日期范围无数据时, THE WebDashboard SHALL 返回空数据集并在页面上显示"暂无数据"提示
8. THE WebDashboard SHALL 提供目标达成率展示页面，以进度条形式展示每个 Usage_Goal 的当日达成状态
9. IF WebDashboard 的依赖库（Flask/FastAPI）未安装, THEN THE Tracker SHALL 在用户执行 `web` 命令时输出安装提示信息

### 需求 5：多设备数据同步

**用户故事：** 作为用户，我希望多台电脑的使用数据能同步到云端，以便生成跨设备的汇总报告，全面了解所有设备的时间分配。

#### 验收标准

1. THE SyncManager SHALL 为每台设备生成唯一的 Device_Profile，包含设备 ID（基于机器硬件信息的哈希值）、设备名称和操作系统信息
2. THE SyncManager SHALL 支持将本地数据目录同步到可配置的远程存储路径（支持本地文件夹路径或 S3 存储桶 URI）
3. WHEN 用户执行 `sync --push` 命令时, THE SyncManager SHALL 将本地数据文件上传到远程存储，文件路径包含设备 ID 前缀以区分不同设备
4. WHEN 用户执行 `sync --pull` 命令时, THE SyncManager SHALL 从远程存储下载所有设备的数据文件到本地临时目录
5. WHEN 用户执行 `sync --report` 命令时, THE SyncManager SHALL 聚合所有设备的数据并生成跨设备汇总报告，包含各设备的使用时长对比和合并后的分类统计
6. THE SyncManager SHALL 在 `config/sync_config.json` 中存储同步配置，包含远程存储路径、设备名称和同步间隔
7. IF 远程存储路径不可访问, THEN THE SyncManager SHALL 输出明确的错误提示并中止同步操作
8. THE SyncManager SHALL 在同步时使用文件修改时间戳避免重复上传未变更的文件

### 需求 6：项目级时间追踪

**用户故事：** 作为开发者，我希望系统不仅按应用分类统计时间，还能按"项目"维度统计，以便了解每个项目的实际投入时间。

#### 验收标准

1. THE ProjectTracker SHALL 检测 VS Code（code.exe）当前打开的工作区路径，通过读取 VS Code 的窗口标题或 `~/.vscode/storage.json` 获取
2. THE ProjectTracker SHALL 检测终端进程（powershell.exe、cmd.exe）的当前工作目录（cwd），通过 psutil 的 Process.cwd() 方法获取
3. THE ProjectTracker SHALL 维护一个项目名称到路径的映射配置文件 `config/projects.json`，用户可手动注册项目
4. WHEN 检测到的工作区路径或 cwd 匹配已注册项目的路径前缀时, THE ProjectTracker SHALL 将该时间段归属到对应项目
5. WHEN 检测到的路径未匹配任何已注册项目时, THE ProjectTracker SHALL 将该时间段归属到"未分类项目"
6. THE ProjectTracker SHALL 在每日报告中新增"项目时间分布"部分，展示每个项目的使用时长和占比
7. WHEN 用户执行 `projects --add` 命令时, THE ProjectTracker SHALL 将项目名称和路径添加到 `config/projects.json`
8. WHEN 用户执行 `projects --list` 命令时, THE ProjectTracker SHALL 列出所有已注册项目及其当日使用时长
9. WHEN 用户执行 `projects --report` 命令时, THE ProjectTracker SHALL 生成指定日期范围内的项目时间汇总报告
10. IF psutil 无法获取某进程的 cwd（权限不足）, THEN THE ProjectTracker SHALL 跳过该进程并记录警告日志

### 需求 7：智能建议引擎

**用户故事：** 作为用户，我希望系统基于历史数据自动识别使用模式并给出个性化建议，以便更有针对性地改善时间管理。

#### 验收标准

1. THE SuggestionEngine SHALL 分析过去 7 天的使用数据，识别每周各天的效率模式（如"周三下午效率最高"）
2. THE SuggestionEngine SHALL 检测连续多天目标未达成的情况，并生成警告类 Suggestion（如"连续 3 天社交时间超标"）
3. THE SuggestionEngine SHALL 识别用户的高效时段模式（基于工作/开发类应用占比最高的时间块），并建议在这些时段安排重要工作
4. THE SuggestionEngine SHALL 识别用户的低效时段模式（基于社交/娱乐类应用占比最高的时间块），并建议在这些时段安排休息或轻量任务
5. WHEN Reporter 生成每日报告时, THE Reporter SHALL 在建议部分展示 SuggestionEngine 生成的个性化建议，替代 V1 中的固定建议模板
6. THE SuggestionEngine SHALL 为每条 Suggestion 附带置信度评分（0-100），基于支撑数据的天数和一致性计算
7. WHEN 历史数据不足 3 天时, THE SuggestionEngine SHALL 回退到 V1 的固定建议模板并提示"数据积累中，建议将在 3 天后更加精准"
8. THE SuggestionEngine SHALL 将生成的建议缓存到 `data/suggestions_cache.json`，避免每次报告生成时重复计算

### 需求 8：休息提醒

**用户故事：** 作为用户，我希望在连续工作一段时间后收到休息提醒（类似 20-20-20 法则），以便保护视力和维持工作效率。

#### 验收标准

1. THE BreakReminder SHALL 支持配置多条 Break_Rule，每条规则包含连续工作阈值（分钟）、建议休息时长（分钟）和提醒方式
2. THE BreakReminder SHALL 默认配置 20-20-20 法则规则：连续工作 20 分钟后提醒休息 20 秒，注视 20 英尺（6 米）外的物体
3. THE BreakReminder SHALL 默认配置长休息规则：连续工作 90 分钟后提醒休息 10 分钟
4. WHEN 用户的前台活跃时间连续达到 Break_Rule 的工作阈值时, THE BreakReminder SHALL 通过 Windows Toast 通知发送休息提醒
5. THE BreakReminder SHALL 基于 ForegroundDetector 的数据判断"连续工作"，当前台窗口持续为工作/开发类应用时视为连续工作
6. WHEN 用户在收到提醒后切换到非工作类应用或锁屏超过指定休息时长时, THE BreakReminder SHALL 重置该规则的工作计时器
7. THE BreakReminder SHALL 在 `config/break_rules.json` 中存储休息规则配置
8. WHEN 用户执行 `break --list` 命令时, THE BreakReminder SHALL 列出所有已配置的 Break_Rule
9. WHEN 用户执行 `break --add` 命令时, THE BreakReminder SHALL 添加新的 Break_Rule 到配置文件
10. THE BreakReminder SHALL 与现有 TimeoutMonitor 模块互补运行，TimeoutMonitor 关注单个应用的累计使用时长，BreakReminder 关注跨应用的连续工作时长

### 需求 9：数据库后端

**用户故事：** 作为用户，我希望系统从 JSON 文件存储迁移到 SQLite 数据库，以便支持更复杂的查询和更高效的数据管理，同时保持零外部依赖部署。

#### 验收标准

1. THE DatabaseBackend SHALL 使用 Python 标准库 sqlite3 模块创建和管理 SQLite 数据库文件 `data/usage_tracker.db`
2. THE DatabaseBackend SHALL 创建 `usage_records` 表，包含字段：id（主键）、timestamp、hour、name、category、cpu、memory_mb、duration_minutes、is_foreground、foreground_minutes、device_id
3. THE DatabaseBackend SHALL 创建 `foreground_sessions` 表，包含字段：id（主键）、app_name、window_title、start_time、end_time、duration_seconds
4. THE DatabaseBackend SHALL 创建 `focus_sessions` 表，包含字段：id（主键）、date、duration_minutes、timestamp、app_name、category
5. THE DatabaseBackend SHALL 创建 `context_switches` 表，包含字段：id（主键）、timestamp、from_app、to_app
6. THE DatabaseBackend SHALL 创建 `project_sessions` 表，包含字段：id（主键）、project_name、app_name、workspace_path、start_time、end_time、duration_minutes
7. THE DatabaseBackend SHALL 提供统一的数据访问接口（DataStore 类），所有模块通过该接口读写数据，而非直接操作文件或数据库
8. THE DatabaseBackend SHALL 提供数据迁移工具，将现有 JSON 数据文件批量导入到 SQLite 数据库
9. WHEN 数据迁移工具执行时, THE DatabaseBackend SHALL 逐个读取 `data/usage_*.json` 文件并将记录插入到 `usage_records` 表中
10. IF 数据库文件不存在, THEN THE DatabaseBackend SHALL 在首次运行时自动创建数据库并初始化所有表结构
11. THE DatabaseBackend SHALL 在 `config.json` 中新增 `storage_backend` 配置项，支持 `"json"` 和 `"sqlite"` 两个值，默认为 `"sqlite"`
12. WHEN `storage_backend` 配置为 `"json"` 时, THE DatabaseBackend SHALL 回退到 V1 的 JSON 文件存储模式，确保向后兼容
13. FOR ALL 通过 DataStore 写入的 Usage_Record，读取后 SHALL 包含与写入时相同的字段值（数据往返一致性）

### 需求 10：系统托盘常驻

**用户故事：** 作为用户，我希望系统在系统托盘常驻运行，实时显示当前应用使用时长，点击可快速查看今日概况，无需每次手动执行命令。

#### 验收标准

1. THE TrayApp SHALL 使用 pystray 库在 Windows 系统托盘区域显示一个图标
2. THE TrayApp SHALL 在托盘图标的悬停提示（tooltip）中实时显示当前前台应用名称和今日累计使用时长
3. WHEN 用户左键点击托盘图标时, THE TrayApp SHALL 显示一个弹出窗口，展示今日使用概况（总时长、Top 3 应用、目标达成状态）
4. WHEN 用户右键点击托盘图标时, THE TrayApp SHALL 显示上下文菜单，包含以下选项：查看今日报告、打开 Web 仪表盘、手动采集、设置、退出
5. THE TrayApp SHALL 在后台持续运行 ForegroundDetector 和 BreakReminder，无需用户手动启动
6. WHEN 用户选择"退出"菜单项时, THE TrayApp SHALL 安全停止所有后台任务并退出进程
7. THE TrayApp SHALL 在 `config.json` 中新增 `tray_enabled` 布尔配置项，默认为 true
8. IF pystray 库未安装, THEN THE Tracker SHALL 在用户执行 `tray` 命令时输出安装提示信息
9. THE TrayApp SHALL 每 60 秒（可配置）刷新一次托盘图标的悬停提示信息
10. WHEN TrayApp 启动时, THE TrayApp SHALL 自动启动数据采集定时器，按 `config.json` 中 `interval_minutes` 的间隔执行采集
