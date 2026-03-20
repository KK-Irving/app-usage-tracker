# 实现计划：应用使用追踪器功能扩展

## 概述

按照依赖关系从底层到上层逐步实现：先修复现有 bug，再统一分类引擎，然后增强各功能模块，最后新增可视化模块并整合统一入口。每个任务构建在前一个任务的基础上，确保无孤立代码。

## 任务列表

- [x] 1. 修复现有代码缺陷并统一分类引擎
  - [x] 1.1 修复 `config/app_categories.json` 格式问题
    - 移除文件头部的 Python 注释行（`# -*- coding: utf-8 -*-` 和 `"""应用分类配置"""`）
    - 将分类配置改为设计文档中定义的结构化格式（包含 `color` 和 `apps` 字段）
    - 确保文件为合法 JSON
    - _需求: 1.3, 2.4_

  - [x] 1.2 重构 `app_categories.py` 统一分类引擎
    - 实现分类优先级顺序：开发 > 工作 > 社交 > 娱乐 > 系统 > 其他
    - 更新 `classify_app()` 按优先级遍历分类
    - 实现 `add_app_to_category(category, app_name)` 和 `remove_app_from_category(category, app_name)` 函数
    - 更新 `CONFIG_FILE` 路径指向 `config/app_categories.json`
    - 更新 `DEFAULT_CATEGORIES` 与设计文档一致（开发、工作、社交、娱乐、系统）
    - 未匹配应用返回 `("其他", "⚪")`
    - _需求: 2.1, 2.2, 2.3, 2.5_

  - [ ]* 1.3 编写分类引擎属性测试
    - **Property 1: 分类优先级一致性** — 同时匹配多个分类时返回优先级更高的分类
    - **验证: 需求 2.2**

  - [ ]* 1.4 编写分类引擎属性测试
    - **Property 2: 分类规则持久化往返** — 添加规则后 classify_app 返回对应分类
    - **验证: 需求 2.3**

  - [ ]* 1.5 编写分类引擎属性测试
    - **Property 3: 未匹配应用默认分类** — 随机字符串返回 ("其他", "⚪")
    - **验证: 需求 2.5**

  - [x] 1.6 修复 `scripts/export_data.py` 语法错误
    - 修复 `export_monthly_csv` 函数中字典字面量缺少的右括号
    - _需求: 1.2_

  - [x] 1.7 修复 `scripts/get_daily_report.py` 语法错误
    - 修复第 248 行附近 `if total_focus = sum(...)` 的赋值语句在 if 条件中的语法错误
    - 将其拆分为先赋值再判断
    - _需求: 1.1_

  - [x] 1.8 修复 `scripts/focus_tracker.py` 导入路径
    - 将 `from app_usage_tracker.app_categories import classify_app` 改为正确的导入路径
    - 使用 `sys.path.insert(0, str(Path(__file__).parent.parent))` 后 `from app_categories import classify_app`
    - _需求: 1.5_

  - [x] 1.9 修复 `scripts/fragment_analyzer.py` 导入路径
    - 将 `from app_usage_tracker.app_categories import classify_app` 改为正确的导入路径
    - 使用 `sys.path.insert(0, str(Path(__file__).parent.parent))` 后 `from app_categories import classify_app`
    - _需求: 1.4_

- [x] 2. 检查点 — 确保所有修复生效
  - 确保所有测试通过，询问用户是否有疑问。

- [x] 3. 增强数据采集与调度模块
  - [x] 3.1 增强 `scripts/collect_usage.py` 数据采集
    - 从 `config.json` 读取 `interval_minutes`、`top_processes`、`exclude_system` 配置项
    - 使用统一分类引擎 `app_categories.classify_app()` 替代内联分类逻辑
    - 当 `exclude_system=true` 时过滤分类为"系统"的进程记录
    - 自动创建数据目录（`mkdir(parents=True, exist_ok=True)`）
    - 实现 `get_process_usage(top_n, exclude_system)` 接口
    - _需求: 3.2, 3.3, 3.4, 3.5_

  - [ ]* 3.2 编写数据采集属性测试
    - **Property 4: 系统进程过滤** — exclude_system=True 时结果不含系统类记录
    - **验证: 需求 3.5**

  - [x] 3.3 增强 `scripts/scheduler.py` 定时调度
    - 实现通过 Windows 任务计划程序（schtasks 命令）设置定时采集任务
    - 替换现有的 OpenClaw cron 方式
    - 提供 `--setup` 命令自动注册 Windows 计划任务
    - _需求: 3.1_

- [x] 4. 增强每日报告与时间块分析
  - [x] 4.1 重构 `scripts/get_daily_report.py` 每日报告
    - 使用统一分类引擎替代内联 `CATEGORY_CONFIG` 和 `categorize_app` 函数
    - 确保报告包含完整 8 个部分：总览、分类汇总、Top 10 应用、时间块分布、专注力分析、碎片时间分析、空闲时间检测、建议
    - 修复建议部分的 f-string 格式错误（`{work_ratio:.1f}%` 缺少 f 前缀）
    - 支持 `--date` 参数指定日期，无数据时输出明确错误提示
    - 报告同时输出到控制台和保存到 `data/reports/daily_YYYY-MM-DD.md`
    - _需求: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 4.2 编写每日报告属性测试
    - **Property 5: 每日报告包含所有必需部分** — 非空记录列表生成的报告包含 8 个部分标题
    - **验证: 需求 4.1**

  - [ ]* 4.3 编写报告建议属性测试
    - **Property 6: 报告建议与数据一致性** — 工作占比低于 30% 时提示增加专注，高于 60% 时正面反馈
    - **验证: 需求 4.5**

  - [x] 4.4 增强时间块分析功能
    - 在 `get_daily_report.py` 中实现高效/低效时段标记逻辑
    - 工作/开发类应用占比超过 60% 标记为"高效时段"
    - 社交/娱乐类应用占比超过 50% 标记为"低效时段"
    - 以可视化进度条展示各时间块使用占比
    - _需求: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 4.5 编写时间块属性测试
    - **Property 7: 时间块映射完备性与统计正确性** — 0-23 小时均映射到 7 个时间块之一，记录数统计正确
    - **验证: 需求 5.1, 5.2**

  - [ ]* 4.6 编写时间块效率标记属性测试
    - **Property 8: 时间块效率标记** — 工作/开发占比 >60% 标记高效，社交/娱乐占比 >50% 标记低效
    - **验证: 需求 5.3, 5.4**

- [x] 5. 检查点 — 确保报告和时间块分析正常
  - 确保所有测试通过，询问用户是否有疑问。

- [x] 6. 增强超时提醒模块
  - [x] 6.1 增强 `scripts/timeout_alert.py` 超时提醒
    - 从 `config/timeout_alerts.json` 加载配置，不存在时使用默认值
    - 实现同一应用同一天仅发送一次通知的去重逻辑
    - 支持 `--check` 立即检查所有应用超时状态
    - 支持 `--add` 和 `--remove` 命令管理告警规则并持久化
    - 使用 Windows Toast 通知发送提醒
    - _需求: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [ ]* 6.2 编写超时检测属性测试
    - **Property 9: 超时检测正确性** — 运行时长超过阈值时包含该应用，未超过时不包含
    - **验证: 需求 6.3**

  - [ ]* 6.3 编写超时通知去重属性测试
    - **Property 10: 超时通知去重（幂等性）** — 同一天内同一应用通知最多触发一次
    - **验证: 需求 6.4**

  - [ ]* 6.4 编写超时规则持久化属性测试
    - **Property 11: 超时规则持久化往返** — 添加规则后加载包含该规则，移除后不包含
    - **验证: 需求 6.5**

- [x] 7. 增强专注力追踪模块
  - [x] 7.1 重构 `scripts/focus_tracker.py` 专注力追踪
    - 使用统一分类引擎，专注度分数 = 工作/开发类应用时长 / 总时长 × 100
    - 实现 4 级专注度标签：≥80 高度专注、60-79 较为专注、40-59 注意力分散、<40 休闲模式
    - 专注会话检测阈值可配置（默认 25 分钟），从 `config.json` 的 `focus_threshold_minutes` 读取
    - 支持番茄钟计时模式，计时结束后记录到 `data/focus_sessions.json`
    - 在专注力报告中按分类展示使用时长占比和可视化进度条
    - _需求: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [ ]* 7.2 编写专注度分数属性测试
    - **Property 12: 专注度分数计算与标签** — 分数等于工作+开发时长占比，标签与分数区间一致
    - **验证: 需求 7.3, 7.4**

  - [ ]* 7.3 编写专注会话属性测试
    - **Property 13: 专注会话仅包含工作/开发类应用** — 检测到的 Focus_Session 中应用全属于工作或开发分类
    - **验证: 需求 7.1, 7.2**

- [x] 8. 增强碎片时间分析模块
  - [x] 8.1 重构 `scripts/fragment_analyzer.py` 碎片时间分析
    - 使用统一分类引擎
    - 碎片阈值从 `config.json` 的 `fragment_time_threshold_minutes` 读取（默认 5 分钟）
    - 碎片化指数 = 活跃小时数 / 总记录数
    - 三级分类：短碎片（< 10 分钟）、中碎片（10-30 分钟）、长使用（> 30 分钟）
    - 基于碎片时间模式给出利用建议
    - _需求: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 8.2 编写碎片时间分类属性测试
    - **Property 14: 碎片时间三级分类** — 任意应用总使用时长归入且仅归入三级之一
    - **验证: 需求 8.1, 8.3**

  - [ ]* 8.3 编写碎片化指数属性测试
    - **Property 15: 碎片化指数计算** — 碎片化指数等于活跃小时数 / 总记录数
    - **验证: 需求 8.2**

- [x] 9. 检查点 — 确保超时、专注力、碎片分析模块正常
  - 确保所有测试通过，询问用户是否有疑问。

- [x] 10. 增强周报/月报与数据导出
  - [x] 10.1 增强 `scripts/analyze_trends.py` 周报/月报
    - 修复 `get_month_dates()` 中本月日期计算逻辑错误
    - 周报聚合 7 天数据并与上周对比，展示数据量变化百分比和 Top 5 应用排名变化
    - 月报聚合本月数据并与上月对比
    - 周报保存到 `data/reports/weekly_YYYY-MM-DD.md`，月报保存到 `data/reports/monthly_YYYY-MM-DD.md`
    - 无对比数据时仅展示当前周期数据并输出提示
    - _需求: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 10.2 编写趋势变化属性测试
    - **Property 16: 趋势变化百分比计算** — 变化百分比 = (本期-上期)/上期×100，上期为 0 时返回 0
    - **验证: 需求 9.3**

  - [x] 10.3 增强 `scripts/export_data.py` 数据导出
    - 确保使用 `utf-8-sig` 编码写入 CSV
    - 支持单日、周、月导出，字段包含 timestamp、hour、Name、Category、CPU、MemoryMB、DurationMinutes
    - 无数据时输出明确错误提示
    - _需求: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ]* 10.4 编写 CSV 导出往返属性测试
    - **Property 17: CSV 导出往返** — 导出后读取回来字段值一致，且使用 utf-8-sig 编码
    - **验证: 需求 10.1, 10.4**

- [x] 11. 新增可视化图表模块
  - [x] 11.1 创建 `scripts/visualizer.py` 可视化模块
    - 实现 `setup_chinese_font()` 配置 matplotlib 中文字体（SimHei → Microsoft YaHei → sans-serif）
    - 实现 `generate_category_pie(records, output_path)` 生成分类使用时长饼图
    - 实现 `generate_hourly_bar(records, output_path)` 生成每小时活跃度柱状图
    - 实现 `generate_weekly_trend(dates, output_path)` 生成周趋势折线图
    - 图表保存为 PNG 到 `data/reports/charts/` 目录
    - 数据不足时输出提示信息而非抛出异常
    - _需求: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [ ]* 11.2 编写图表生成属性测试
    - **Property 18: 图表文件生成** — 至少两个分类的非空记录列表生成后存在大小 >0 的 PNG 文件
    - **验证: 需求 11.4**

- [x] 12. 整合统一命令行入口
  - [x] 12.1 更新 `app_usage_tracker.py` 统一入口
    - 新增 `timeout` 命令路由到 `scripts/timeout_alert.py`
    - 新增 `chart` 命令路由到 `scripts/visualizer.py`
    - 确保所有子模块导入路径正确
    - 未知命令或无参数时输出帮助信息，列出所有可用命令
    - 更新帮助文本包含所有 11 个命令：collect、daily、weekly、monthly、focus、fragments、export、categories、timeout、chart、help
    - _需求: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [ ]* 12.2 编写命令行入口属性测试
    - **Property 19: 未知命令输出帮助** — 不在已知命令列表中的字符串作为参数时输出帮助信息
    - **验证: 需求 12.3**

- [x] 13. 最终检查点 — 确保所有模块集成正常
  - 确保所有测试通过，询问用户是否有疑问。

## 说明

- 标记 `*` 的任务为可选测试任务，可跳过以加快 MVP 进度
- 每个任务引用了具体的需求编号，确保可追溯性
- 检查点任务用于阶段性验证，确保增量式开发的稳定性
- 属性测试使用 Hypothesis 库，验证设计文档中定义的 19 个正确性属性
- 单元测试和属性测试互补，共同提供全面的测试覆盖
