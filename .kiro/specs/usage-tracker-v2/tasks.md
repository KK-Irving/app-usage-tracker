# 实现计划：App Usage Tracker V2 — 十大扩展功能

## 概览

按模块依赖顺序实现 V2 的十大扩展功能。DataStore 作为基础设施最先实现，各业务模块依次构建，最后通过 TrayApp 整合所有功能。每个模块包含核心实现和对应的属性测试/单元测试子任务。

## 任务

- [x] 1. 实现 DataStore 统一数据访问层（需求 9）
  - [x] 1.1 创建 `scripts/data_store.py`，实现 DataStore 类、SQLiteBackend 和 JSONBackend
    - 实现 DataStore 类，根据 `config.json` 的 `storage_backend` 配置选择后端
    - 实现 SQLiteBackend：创建 `data/usage_tracker.db`，初始化所有表结构（usage_records、foreground_sessions、focus_sessions、context_switches、project_sessions），包含所有索引
    - 实现 JSONBackend：兼容 V1 的 `{"date": "...", "records": [...]}` 格式
    - 实现所有数据访问方法：save_usage_records、get_usage_records、get_usage_records_range、save_foreground_session、get_foreground_sessions、save_context_switch、get_context_switches、save_project_session、get_project_sessions、save_focus_session、get_focus_sessions、query
    - 数据库文件不存在时自动创建并初始化表结构
    - 在 `config.json` 中新增 `storage_backend` 配置项，默认为 `"sqlite"`
    - _需求: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.10, 9.11, 9.12, 9.13_

  - [ ]* 1.2 编写 DataStore 往返一致性属性测试
    - **Property 26: DataStore 往返一致性**
    - 使用 hypothesis 生成随机 Usage_Record，验证写入后读取字段值一致
    - 测试 SQLite 和 JSON 双后端
    - **验证: 需求 9.13, 1.5, 1.8**

  - [ ]* 1.3 编写 JSON 后端 V1 兼容性属性测试
    - **Property 27: JSON 后端 V1 兼容性**
    - 验证 JSON 后端写入的数据保持 V1 格式，V1 的 load_today_data() 可正确读取
    - **验证: 需求 9.12**

- [x] 2. 实现数据迁移工具（需求 9）
  - [x] 2.1 创建 `scripts/db_migrate.py`，实现 JSON→SQLite 迁移工具
    - 遍历 `data/usage_*.json` 文件，逐个读取并插入到 usage_records 表
    - 迁移 `data/focus_sessions.json` 到 focus_sessions 表
    - 支持 `--dry-run` 模式预览迁移数据量
    - 输出迁移进度和结果统计
    - _需求: 9.8, 9.9_

  - [ ]* 2.2 编写数据迁移等价性属性测试
    - **Property 25: 数据迁移等价性**
    - 使用 hypothesis 生成随机 V1 格式 JSON 数据，迁移后验证 DataStore 查询结果与原始数据一致
    - **验证: 需求 9.8, 9.9**

- [x] 3. 检查点 — 确保 DataStore 和迁移工具测试通过
  - 确保所有测试通过，如有问题请向用户确认。

- [x] 4. 实现 ForegroundDetector 前台窗口检测（需求 1）
  - [x] 4.1 创建 `scripts/foreground_detector.py`，实现 ForegroundDetector 类
    - 通过 win32gui.GetForegroundWindow() 和 GetWindowText() 获取前台窗口
    - 通过 GetWindowThreadProcessId() 获取 PID，再用 psutil.Process(pid).name() 获取进程名
    - 实现可配置采样间隔（默认 1 秒，从 config.json 的 foreground_interval_seconds 读取）
    - 实现 _poll_loop 轮询逻辑：检测窗口变化、累加会话时长
    - 实现 _on_window_change：结束当前会话、持久化到 DataStore、记录切换事件、创建新会话
    - 实现 start/stop 后台线程控制
    - 实现 get_current_foreground 供 TrayApp 使用
    - pywin32 不可用时降级：_win32gui_available = False，输出警告，get_foreground_window 返回 None
    - _需求: 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 1.8_

  - [ ]* 4.2 编写前台会话属性测试
    - **Property 1: 窗口切换产生前台会话**
    - 模拟窗口状态序列，验证窗口变化时产生 Foreground_Session
    - **验证: 需求 1.2**

  - [ ]* 4.3 编写前台会话时长累加属性测试
    - **Property 2: 前台会话时长累加**
    - 验证连续 N 个采样间隔内窗口不变时，duration_seconds = N × 采样间隔
    - **验证: 需求 1.4**

- [x] 5. 实现 GoalManager 目标设定与达成率（需求 2）
  - [x] 5.1 创建 `scripts/goal_manager.py`，实现 GoalManager 类和 UsageGoal 数据类
    - 实现目标 CRUD：add_goal、remove_goal、list_goals
    - 持久化到 `config/usage_goals.json`
    - 支持按分类名称或应用名称设定目标
    - 支持 min（下限）和 max（上限）两种目标类型
    - 实现 evaluate(date)：计算达成率（actual/target×100%），判定达成状态
    - 实现 evaluate_weekly()：过去 7 天达成趋势
    - _需求: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9_

  - [ ]* 5.2 编写目标达成率评估属性测试
    - **Property 3: 目标达成率评估正确性**
    - 使用 hypothesis 生成随机 actual_minutes、target_minutes、goal_type，验证 achieved 和 achievement_rate 计算正确
    - **验证: 需求 2.1, 2.4, 2.5, 2.6**

  - [ ]* 5.3 编写目标 CRUD 往返一致性属性测试
    - **Property 4: 目标 CRUD 往返一致性**
    - 使用 hypothesis 生成随机添加/移除操作序列，验证 list_goals 结果一致
    - **验证: 需求 2.2, 2.8, 2.9**

- [x] 6. 实现 SwitchAnalyzer 应用切换频率分析（需求 3）
  - [x] 6.1 创建 `scripts/switch_analyzer.py`，实现 SwitchAnalyzer 类
    - 实现 get_hourly_switch_counts(date)：每小时切换次数统计
    - 实现 get_high_frequency_hours(date)：检测异常高频时段（> 平均值 × 1.5）
    - 实现 get_context_switch_cost(date)：切换次数 × DEFAULT_RECOVERY_MINUTES（2 分钟）
    - 实现 get_top_switch_pairs(date, top_n)：最频繁切换对 Top N
    - 实现 get_switch_focus_correlation(date)：切换频率与专注度相关性
    - _需求: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [ ]* 6.2 编写每小时切换次数属性测试
    - **Property 5: 每小时切换次数统计**
    - 使用 hypothesis 生成随机 Context_Switch 事件，验证每小时计数正确
    - **验证: 需求 3.1**

  - [ ]* 6.3 编写高频切换时段检测属性测试
    - **Property 6: 高频切换时段检测**
    - 验证返回的时段恰好是切换次数 > 平均值 × 1.5 的时段
    - **验证: 需求 3.3**

  - [ ]* 6.4 编写上下文切换成本属性测试
    - **Property 7: 上下文切换成本计算**
    - 验证返回值 = 事件总数 × DEFAULT_RECOVERY_MINUTES
    - **验证: 需求 3.4**

  - [ ]* 6.5 编写 Top 切换对排序属性测试
    - **Property 8: Top 切换对排序**
    - 验证返回的切换对按频次降序排列，长度 ≤ top_n
    - **验证: 需求 3.6**

  - [ ]* 6.6 编写切换-专注相关性边界属性测试
    - **Property 9: 切换-专注相关性边界**
    - 验证 correlation 值在 [-1, 1] 范围内
    - **验证: 需求 3.7**

- [x] 7. 检查点 — 确保核心模块测试通过
  - 确保所有测试通过，如有问题请向用户确认。

- [x] 8. 实现 ProjectTracker 项目级时间追踪（需求 6）
  - [x] 8.1 创建 `scripts/project_tracker.py`，实现 ProjectTracker 类
    - 实现项目 CRUD：add_project、remove_project、list_projects，持久化到 `config/projects.json`
    - 实现 detect_project(app_name, window_title)：
      - VS Code：从窗口标题解析项目名（格式 "文件名 - 项目名 - Visual Studio Code"）
      - 终端：通过 psutil.Process.cwd() 获取工作目录
      - 匹配已注册项目的路径前缀（最长前缀匹配）
      - 未匹配返回"未分类项目"
    - 实现 get_project_report(date) 和 get_project_report_range(start, end)
    - psutil 无法获取 cwd 时跳过并记录警告
    - _需求: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10_

  - [ ]* 8.2 编写 VS Code 窗口标题解析属性测试
    - **Property 15: VS Code 窗口标题解析**
    - 使用 hypothesis 生成符合格式的窗口标题，验证正确提取项目名
    - **验证: 需求 6.1**

  - [ ]* 8.3 编写项目路径匹配属性测试
    - **Property 16: 项目路径匹配**
    - 验证最长前缀匹配逻辑，无匹配时返回"未分类项目"
    - **验证: 需求 6.4, 6.5**

  - [ ]* 8.4 编写项目 CRUD 往返一致性属性测试
    - **Property 17: 项目 CRUD 往返一致性**
    - 使用 hypothesis 生成随机添加/移除操作序列，验证 list_projects 结果一致
    - **验证: 需求 6.3, 6.7, 6.8**

- [x] 9. 实现 SuggestionEngine 智能建议引擎（需求 7）
  - [x] 9.1 创建 `scripts/suggestion_engine.py`，实现 SuggestionEngine 类和 Suggestion 数据类
    - 实现 _detect_efficiency_patterns：分析过去 7 天效率模式
    - 实现 _detect_goal_streaks：检测连续 ≥ 3 天目标未达成
    - 实现 _detect_peak_hours：识别高效/低效时段
    - 实现 _calculate_confidence：置信度 = min(100, data_days × 10 + consistency × 50)
    - 实现建议缓存：_save_cache / _load_cache（当日有效）
    - 实现 get_suggestions_or_fallback：数据 < 3 天回退到 V1 固定模板
    - _需求: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_

  - [ ]* 9.2 编写效率模式检测属性测试
    - **Property 18: 效率模式检测**
    - 验证识别的"最高效日"是工作/开发类应用占比最高的那一天
    - **验证: 需求 7.1**

  - [ ]* 9.3 编写连续目标未达成警告属性测试
    - **Property 19: 连续目标未达成警告**
    - 验证连续 ≥ 3 天未达成时生成 warning 类型 Suggestion
    - **验证: 需求 7.2**

  - [ ]* 9.4 编写高效/低效时段识别属性测试
    - **Property 20: 高效/低效时段识别**
    - 验证高效时段是工作/开发占比最高的时间块，低效时段是社交/娱乐占比最高的时间块
    - **验证: 需求 7.3, 7.4**

  - [ ]* 9.5 编写置信度评分边界属性测试
    - **Property 21: 置信度评分边界**
    - 验证所有 Suggestion 的 confidence 在 [0, 100] 范围内
    - **验证: 需求 7.6**

  - [ ]* 9.6 编写建议缓存往返一致性属性测试
    - **Property 22: 建议缓存往返一致性**
    - 验证 _save_cache 后 _load_cache 返回等价的建议列表
    - **验证: 需求 7.8**

- [x] 10. 实现 SyncManager 多设备数据同步（需求 5）
  - [x] 10.1 创建 `scripts/sync_manager.py`，实现 SyncManager 类和 DeviceProfile 数据类
    - 实现 _generate_device_id：基于 uuid.getnode() 的 SHA256 哈希
    - 实现 _get_or_create_device：从 sync_config.json 加载或创建设备配置
    - 实现 push：上传本地数据到远程存储，路径包含 device_id 前缀，跳过未变更文件
    - 实现 pull：下载所有设备数据到 data/sync_temp/{device_id}/
    - 实现 generate_cross_device_report：聚合所有设备数据，生成跨设备汇总
    - 支持本地文件夹路径和 S3 URI（boto3 可选）
    - 远程路径不可访问时输出错误并中止
    - _需求: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

  - [ ]* 10.2 编写设备 ID 确定性属性测试
    - **Property 11: 设备 ID 确定性**
    - 验证同一台机器多次调用 _generate_device_id 返回相同值
    - **验证: 需求 5.1**

  - [ ]* 10.3 编写同步推送路径格式属性测试
    - **Property 12: 同步推送路径格式**
    - 验证 push 生成的远程路径包含 device_id 前缀
    - **验证: 需求 5.3**

  - [ ]* 10.4 编写跨设备聚合一致性属性测试
    - **Property 13: 跨设备聚合一致性**
    - 验证合并分类统计总时长等于各设备分类时长之和
    - **验证: 需求 5.5**

  - [ ]* 10.5 编写同步跳过未变更文件属性测试
    - **Property 14: 同步跳过未变更文件**
    - 验证文件修改时间未变化时 push 跳过该文件
    - **验证: 需求 5.8**

- [x] 11. 实现 BreakReminder 休息提醒（需求 8）
  - [x] 11.1 创建 `scripts/break_reminder.py`，实现 BreakReminder 类和 BreakRule 数据类
    - 实现默认规则：20-20-20 法则（20 分钟工作 → 20 秒休息）和长休息（90 分钟 → 10 分钟休息）
    - 实现规则 CRUD：add_rule、list_rules，持久化到 `config/break_rules.json`
    - 实现 _monitor_loop：基于 ForegroundDetector 判断连续工作，达到阈值发送 Toast 通知
    - 实现计时器重置：切换到非工作类应用或锁屏超过休息时长时重置
    - 复用 timeout_alert.py 的 send_notification 函数
    - 与 TimeoutMonitor 互补运行
    - _需求: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 8.10_

  - [ ]* 11.2 编写休息提醒状态机属性测试
    - **Property 23: 休息提醒状态机**
    - 验证连续工作时长 ≥ 阈值时触发提醒，切换到非工作类应用且持续 ≥ 休息时长时重置计时器
    - **验证: 需求 8.4, 8.5, 8.6**

  - [ ]* 11.3 编写休息规则 CRUD 往返一致性属性测试
    - **Property 24: 休息规则 CRUD 往返一致性**
    - 验证添加操作后 list_rules 包含所有已添加的规则
    - **验证: 需求 8.1, 8.7, 8.8, 8.9**

- [x] 12. 检查点 — 确保所有业务模块测试通过
  - 确保所有测试通过，如有问题请向用户确认。

- [x] 13. 实现 WebDashboard Web 仪表盘（需求 4）
  - [x] 13.1 创建 `scripts/web_dashboard.py`，实现 Flask 应用和 RESTful API
    - 实现 create_app(data_store)，默认监听 127.0.0.1:8080
    - 实现 API 端点：/api/usage/today、/api/usage（支持 start/end/category 参数）、/api/usage/categories、/api/goals、/api/switches、/api/projects
    - 无数据时返回空数据集
    - Flask 未安装时输出安装提示
    - _需求: 4.1, 4.6, 4.7, 4.9_

  - [x] 13.2 创建 Web 仪表盘前端模板
    - 创建 `templates/base.html`：基础布局模板
    - 创建 `templates/dashboard.html`：首页仪表盘（今日概览、分类占比、Top 5 应用）
    - 创建 `templates/goals.html`：目标达成率页面（进度条展示）
    - 使用 ECharts（CDN）渲染交互式图表（饼图、柱状图、折线图）
    - 实现日期选择器和分类筛选功能
    - _需求: 4.2, 4.3, 4.4, 4.5, 4.8_

  - [ ]* 13.3 编写分类筛选正确性属性测试
    - **Property 10: 分类筛选正确性**
    - 使用 Flask test_client 验证 /api/usage?category=X 返回的所有记录 Category 等于 X
    - **验证: 需求 4.4, 4.6**

- [x] 14. 实现 V1 模块集成改造
  - [x] 14.1 改造 Collector（`scripts/collect_usage.py`）
    - 改为通过 DataStore 写入数据（替代直接操作 JSON 文件）
    - Usage_Record 新增 is_foreground 和 foreground_minutes 字段
    - 从 ForegroundDetector 获取前台数据填充新字段
    - 保持 V1 命令行接口不变
    - _需求: 1.5, 1.6, 9.7_

  - [x] 14.2 改造 Reporter（`scripts/get_daily_report.py`）
    - 改为通过 DataStore 读取数据
    - 新增"目标达成率"报告部分（调用 GoalManager.evaluate）
    - 新增"切换分析"报告部分（调用 SwitchAnalyzer）
    - 新增"项目时间分布"报告部分（调用 ProjectTracker）
    - 建议部分改为调用 SuggestionEngine（替代固定模板）
    - 分别展示前台活跃时间和后台运行时间
    - _需求: 1.6, 2.4, 2.7, 3.5, 6.6, 7.5_

  - [x] 14.3 改造 FocusTracker（`scripts/focus_tracker.py`）
    - 改为通过 DataStore 读写专注会话
    - 与 SwitchAnalyzer 关联，提供切换频率-专注度相关性数据
    - _需求: 3.7_

  - [x] 14.4 改造周报/月报（`scripts/analyze_trends.py`）
    - 改为通过 DataStore 读取数据
    - 周报新增目标达成趋势展示（过去 7 天达成率）
    - _需求: 2.7_

- [x] 15. 更新统一命令行入口（`app_usage_tracker.py`）
  - 新增命令注册：goals、switches、projects、web、sync、break、tray、migrate
  - goals 命令：--add、--remove、--list、--evaluate
  - switches 命令：--date 参数
  - projects 命令：--add、--remove、--list、--report
  - web 命令：启动 Web 仪表盘
  - sync 命令：--push、--pull、--report
  - break 命令：--add、--list、--start
  - tray 命令：启动系统托盘
  - migrate 命令：执行 JSON→SQLite 迁移
  - 更新 help 信息
  - _需求: 2.8, 2.9, 6.7, 6.8, 6.9, 8.8, 8.9_

- [x] 16. 检查点 — 确保集成改造和命令行入口测试通过
  - 确保所有测试通过，如有问题请向用户确认。

- [x] 17. 实现 TrayApp 系统托盘常驻（需求 10）
  - [x] 17.1 创建 `scripts/tray_app.py`，实现 TrayApp 类
    - 使用 pystray 创建系统托盘图标
    - 实现 tooltip 实时显示：当前前台应用名称 + 今日累计使用时长，每 60 秒刷新
    - 实现左键点击弹窗：今日概况（总时长、Top 3 应用、目标达成状态）
    - 实现右键菜单：查看今日报告、打开 Web 仪表盘、手动采集、设置、退出
    - 启动时自动启动 ForegroundDetector 和 BreakReminder 后台线程
    - 启动数据采集定时器（按 config.json 的 interval_minutes 间隔）
    - 退出时安全停止所有后台任务
    - pystray 未安装时输出安装提示
    - 在 config.json 新增 tray_enabled 和 tray_refresh_seconds 配置项
    - _需求: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9, 10.10_

- [x] 18. 最终检查点 — 全量测试通过
  - 确保所有测试通过，如有问题请向用户确认。
  - 运行 `pytest tests/ -v` 验证所有属性测试和单元测试
  - 验证所有 27 条正确性属性均有对应的属性测试覆盖

## 备注

- 标记 `*` 的子任务为可选测试任务，可跳过以加速 MVP 开发
- 每个任务引用了具体的需求编号，确保需求可追溯
- 检查点任务用于阶段性验证，确保增量开发的正确性
- 属性测试使用 hypothesis 库，每个测试至少运行 100 次迭代
- 所有模块通过 DataStore 统一接口访问数据，确保存储后端可切换
