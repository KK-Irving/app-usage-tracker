# -*- coding: utf-8 -*-
"""
应用使用追踪器 - 统一命令行入口
支持：采集、报告、分析、导出、图表、超时提醒
"""
import sys
from pathlib import Path

# 确保可以导入子模块
sys.path.insert(0, str(Path(__file__).parent))

# 修复 Windows 控制台编码
try:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
except Exception:
    pass

from app_categories import (
    classify_app, load_categories, save_categories,
    add_app_to_category, remove_app_from_category, DEFAULT_CATEGORIES
)

ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"
REPORT_DIR = DATA_DIR / "reports"


def show_help():
    """显示帮助信息"""
    help_text = f"""
📱 App Usage Tracker V2 - 应用使用追踪器

使用方法: python app_usage_tracker.py <命令> [选项]

命令:
  collect             采集当前应用数据
  daily [--date D]    生成每日报告
  weekly              生成周报
  monthly             生成月报
  focus [--timer N]   专注力分析 / 番茄钟计时
  fragments           碎片时间分析
  export [选项]       导出数据 (--daily/--weekly/--monthly)
  categories [选项]   管理应用分类 (add/remove/reset)
  timeout [选项]      超时提醒 (--check/--add/--remove/--list)
  chart [选项]        生成可视化图表 (--pie/--bar/--trend)
  schedule [选项]     定时任务管理
  goals [选项]        目标管理 (--add/--remove/--list/--evaluate)
  switches [--date D] 应用切换分析
  projects [选项]     项目管理 (--add/--remove/--list/--report)
  web                 启动 Web 仪表盘
  sync [选项]         多设备同步 (--push/--pull/--report)
  break [选项]        休息提醒 (--add/--list/--start)
  tray                启动系统托盘
  migrate             执行 JSON→SQLite 数据迁移
  help                显示帮助

示例:
  python app_usage_tracker.py collect
  python app_usage_tracker.py daily --date 2026-03-19
  python app_usage_tracker.py goals --add 开发 min 240
  python app_usage_tracker.py goals --evaluate
  python app_usage_tracker.py switches --date 2026-03-19
  python app_usage_tracker.py projects --add myproject E:/projects/myproject
  python app_usage_tracker.py web
  python app_usage_tracker.py sync --push
  python app_usage_tracker.py break --start
  python app_usage_tracker.py tray
  python app_usage_tracker.py migrate

数据位置: {DATA_DIR}
报告位置: {REPORT_DIR}
"""
    print(help_text)


def run_collection():
    """执行数据采集"""
    from scripts.collect_usage import collect
    collect()


def run_daily_report():
    """生成每日报告"""
    date_str = None
    if '--date' in sys.argv:
        idx = sys.argv.index('--date')
        if idx + 1 < len(sys.argv):
            date_str = sys.argv[idx + 1]
    from scripts.get_daily_report import generate_report, main as report_main
    if date_str:
        # 直接传参
        sys.argv = ['get_daily_report.py', '--date', date_str]
        report_main()
    else:
        report_main()


def run_weekly_report():
    """生成周报"""
    from scripts.analyze_trends import generate_weekly_report
    generate_weekly_report()


def run_monthly_report():
    """生成月报"""
    from scripts.analyze_trends import generate_monthly_report
    generate_monthly_report()


def run_focus_analysis():
    """专注力分析"""
    timer = None
    if '--timer' in sys.argv:
        idx = sys.argv.index('--timer')
        if idx + 1 < len(sys.argv):
            timer = int(sys.argv[idx + 1])

    if timer is not None:
        from scripts.focus_tracker import start_focus_timer
        start_focus_timer(timer)
    else:
        from scripts.focus_tracker import analyze_daily_focus
        analyze_daily_focus()


def run_fragment_analysis():
    """碎片时间分析"""
    from scripts.fragment_analyzer import generate_fragment_report
    generate_fragment_report()


def run_export():
    """数据导出"""
    from scripts.export_data import export_daily_csv, export_weekly_csv, export_monthly_csv
    from datetime import datetime

    args = sys.argv[2] if len(sys.argv) > 2 else '--daily'
    arg = args.lstrip('-')

    if arg == 'weekly':
        export_weekly_csv()
    elif arg == 'monthly':
        export_monthly_csv()
    else:
        date = sys.argv[3] if len(sys.argv) > 3 else datetime.now().strftime("%Y-%m-%d")
        export_daily_csv(date)


def manage_categories():
    """管理应用分类"""
    args = sys.argv[2:]
    if not args:
        categories = load_categories()
        print("\n🏷️ 当前应用分类:")
        print("-" * 50)
        for name, info in categories.items():
            apps = ", ".join(info.get('apps', [])[:5])
            if len(info.get('apps', [])) > 5:
                apps += "..."
            print(f"  {info.get('color', '⚪')} {name:<8} {apps}")
        print("-" * 50)
    elif args[0] == 'reset':
        save_categories(DEFAULT_CATEGORIES)
        print("✅ 已重置为默认分类")
    elif args[0] == 'add' and len(args) >= 3:
        if add_app_to_category(args[1], args[2]):
            print(f"✅ 已将 {args[2]} 添加到 {args[1]}")
        else:
            print(f"⚠️ {args[2]} 已在 {args[1]} 分类中")
    elif args[0] == 'remove' and len(args) >= 3:
        if remove_app_from_category(args[1], args[2]):
            print(f"✅ 已将 {args[2]} 从 {args[1]} 移除")
        else:
            print(f"❌ 未找到 {args[2]} 在 {args[1]} 中")
    else:
        print("用法: categories [add|remove|reset] [分类名] [应用名]")


def run_timeout():
    """超时提醒"""
    # 传递剩余参数给 timeout_alert
    original_argv = sys.argv
    sys.argv = ['timeout_alert.py'] + sys.argv[2:]
    from scripts.timeout_alert import main as timeout_main
    timeout_main()
    sys.argv = original_argv


def run_chart():
    """生成可视化图表"""
    date = None
    if '--date' in sys.argv:
        idx = sys.argv.index('--date')
        if idx + 1 < len(sys.argv):
            date = sys.argv[idx + 1]

    from scripts.visualizer import (
        generate_category_pie, generate_hourly_bar,
        generate_weekly_trend, generate_all_charts, load_data
    )
    from datetime import datetime

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    if '--pie' in sys.argv:
        data = load_data(date)
        if data:
            generate_category_pie(data.get('records', []))
    elif '--bar' in sys.argv:
        data = load_data(date)
        if data:
            generate_hourly_bar(data.get('records', []))
    elif '--trend' in sys.argv:
        generate_weekly_trend()
    else:
        generate_all_charts(date)


def run_schedule():
    """定时任务管理"""
    original_argv = sys.argv
    sys.argv = ['scheduler.py'] + sys.argv[2:]
    from scripts.scheduler import main as scheduler_main
    scheduler_main()
    sys.argv = original_argv


def run_goals():
    """目标管理"""
    from scripts.data_store import DataStore
    from scripts.goal_manager import GoalManager
    store = DataStore()
    gm = GoalManager(store)
    args = sys.argv[2:]

    if not args or '--list' in args:
        goals = gm.list_goals()
        if not goals:
            print("📋 暂无目标配置")
        else:
            print("📋 当前目标:")
            results = gm.evaluate()
            for r in results:
                g = r["goal"]
                status = "✅" if r["achieved"] else "❌"
                t = "≥" if g.goal_type == "min" else "≤"
                print(f"  {g.target} ({t}{int(g.minutes)}min): {int(r['actual_minutes'])}min {status}")
    elif '--add' in args:
        idx = args.index('--add')
        if idx + 3 <= len(args):
            target, goal_type, minutes = args[idx+1], args[idx+2], args[idx+3]
            gm.add_goal(target, goal_type, float(minutes))
            print(f"✅ 已添加目标: {target} {goal_type} {minutes}min")
        else:
            print("用法: goals --add <目标名> <min|max> <分钟数>")
    elif '--remove' in args:
        idx = args.index('--remove')
        if idx + 1 < len(args):
            if gm.remove_goal(args[idx+1]):
                print(f"✅ 已移除目标: {args[idx+1]}")
            else:
                print(f"❌ 未找到目标: {args[idx+1]}")
    elif '--evaluate' in args:
        results = gm.evaluate()
        if not results:
            print("📋 暂无目标配置")
        else:
            print("🎯 今日目标达成率:")
            for r in results:
                g = r["goal"]
                status = "✅ 达成" if r["achieved"] else "❌ 未达成"
                print(f"  {g.target}: {r['achievement_rate']:.0f}% {status}")
    store.close()


def run_switches():
    """应用切换分析"""
    from scripts.data_store import DataStore
    from scripts.switch_analyzer import SwitchAnalyzer
    from datetime import datetime
    store = DataStore()
    sa = SwitchAnalyzer(store)
    date = datetime.now().strftime("%Y-%m-%d")
    if '--date' in sys.argv:
        idx = sys.argv.index('--date')
        if idx + 1 < len(sys.argv):
            date = sys.argv[idx + 1]

    hourly = sa.get_hourly_switch_counts(date)
    cost = sa.get_context_switch_cost(date)
    top_pairs = sa.get_top_switch_pairs(date)
    high_freq = sa.get_high_frequency_hours(date)

    print(f"🔄 应用切换分析 ({date})")
    print(f"  总切换次数: {sum(hourly.values())}")
    print(f"  上下文切换成本: {cost:.0f} 分钟")
    if high_freq:
        print(f"  高频切换时段: {', '.join(f'{h}:00' for h in high_freq)}")
    if top_pairs:
        print("  Top 切换对:")
        for f_app, t_app, cnt in top_pairs:
            print(f"    {f_app} ↔ {t_app}: {cnt} 次")
    store.close()


def run_projects():
    """项目管理"""
    from scripts.data_store import DataStore
    from scripts.project_tracker import ProjectTracker
    from datetime import datetime
    store = DataStore()
    pt = ProjectTracker(store)
    args = sys.argv[2:]

    if '--add' in args:
        idx = args.index('--add')
        if idx + 2 <= len(args):
            pt.add_project(args[idx+1], args[idx+2])
            print(f"✅ 已注册项目: {args[idx+1]} → {args[idx+2]}")
        else:
            print("用法: projects --add <项目名> <路径>")
    elif '--remove' in args:
        idx = args.index('--remove')
        if idx + 1 < len(args):
            if pt.remove_project(args[idx+1]):
                print(f"✅ 已移除项目: {args[idx+1]}")
            else:
                print(f"❌ 未找到项目: {args[idx+1]}")
    elif '--report' in args:
        date = datetime.now().strftime("%Y-%m-%d")
        report = pt.get_project_report(date)
        print(f"📁 项目时间分布 ({date}):")
        for p in report:
            print(f"  {p['name']:<20} {int(p['minutes']//60)}h {int(p['minutes']%60)}m ({p['pct']:.1f}%)")
    else:
        projects = pt.list_projects()
        if not projects:
            print("📋 暂无注册项目")
        else:
            print("📋 已注册项目:")
            for name, path in projects.items():
                print(f"  {name}: {path}")
    store.close()


def run_web():
    """启动 Web 仪表盘"""
    try:
        from scripts.data_store import DataStore
        from scripts.web_dashboard import run_dashboard
        store = DataStore()
        config = {}
        try:
            import json
            with open(ROOT_DIR / "config.json", 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass
        host = config.get("web_host", "127.0.0.1")
        port = config.get("web_port", 8080)
        run_dashboard(store, host=host, port=port)
    except ImportError:
        print("❌ Flask 未安装。安装: pip install flask")


def run_sync():
    """多设备同步"""
    from scripts.data_store import DataStore
    from scripts.sync_manager import SyncManager
    store = DataStore()
    sm = SyncManager(store)
    args = sys.argv[2:]

    if '--push' in args:
        sm.push()
    elif '--pull' in args:
        sm.pull()
    elif '--report' in args:
        sm.generate_cross_device_report()
    else:
        print("用法: sync --push | --pull | --report")
    store.close()


def run_break():
    """休息提醒"""
    from scripts.data_store import DataStore
    from scripts.foreground_detector import ForegroundDetector
    from scripts.break_reminder import BreakReminder
    args = sys.argv[2:]

    if '--list' in args:
        store = DataStore()
        fg = ForegroundDetector(store)
        br = BreakReminder(fg)
        rules = br.list_rules()
        print("📋 休息规则:")
        for r in rules:
            print(f"  工作 {r.work_threshold_minutes}min → 休息 {r.break_duration_minutes}min: {r.reminder_message}")
        store.close()
    elif '--add' in args:
        idx = args.index('--add')
        if idx + 3 <= len(args):
            store = DataStore()
            fg = ForegroundDetector(store)
            br = BreakReminder(fg)
            br.add_rule(float(args[idx+1]), float(args[idx+2]), args[idx+3])
            print(f"✅ 已添加休息规则")
            store.close()
        else:
            print("用法: break --add <工作阈值分钟> <休息时长分钟> <提醒消息>")
    elif '--start' in args:
        store = DataStore()
        fg = ForegroundDetector(store)
        br = BreakReminder(fg)
        fg.start()
        br.start()
        print("🔔 休息提醒已启动 (Ctrl+C 停止)")
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            br.stop()
            fg.stop()
            print("\n✅ 休息提醒已停止")
        store.close()
    else:
        print("用法: break --list | --add | --start")


def run_tray():
    """启动系统托盘"""
    try:
        from scripts.data_store import DataStore
        from scripts.tray_app import TrayApp
        from scripts.foreground_detector import ForegroundDetector
        from scripts.break_reminder import BreakReminder
        store = DataStore()
        fg = ForegroundDetector(store)
        br = BreakReminder(fg)
        tray = TrayApp(store, fg, br)
        tray.start()
    except ImportError as e:
        if "pystray" in str(e):
            print("❌ pystray 未安装。安装: pip install pystray Pillow")
        else:
            print(f"❌ 依赖缺失: {e}")


def run_migrate():
    """执行 JSON→SQLite 数据迁移"""
    from scripts.db_migrate import migrate
    dry_run = '--dry-run' in sys.argv
    migrate(dry_run=dry_run)


COMMANDS = {
    'collect': run_collection,
    'daily': run_daily_report,
    'weekly': run_weekly_report,
    'monthly': run_monthly_report,
    'focus': run_focus_analysis,
    'fragments': run_fragment_analysis,
    'export': run_export,
    'categories': manage_categories,
    'timeout': run_timeout,
    'chart': run_chart,
    'schedule': run_schedule,
    'goals': run_goals,
    'switches': run_switches,
    'projects': run_projects,
    'web': run_web,
    'sync': run_sync,
    'break': run_break,
    'tray': run_tray,
    'migrate': run_migrate,
    'help': show_help,
}


def main():
    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()

    if command in COMMANDS:
        COMMANDS[command]()
    else:
        print(f"❌ 未知命令: {command}")
        show_help()


if __name__ == "__main__":
    main()
