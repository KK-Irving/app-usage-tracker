# -*- coding: utf-8 -*-
"""
应用使用追踪器 - 统一命令行入口
支持：采集、报告、分析、导出、图表、超时提醒
"""
import sys
from pathlib import Path

# 确保可以导入子模块
sys.path.insert(0, str(Path(__file__).parent))

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
📱 App Usage Tracker - 应用使用追踪器

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
                      --setup-all   一键设置所有定时任务
                      --setup       设置定时采集
                      --setup-report 设置每日报告 (默认23:00)
                      --setup-export 设置每日导出 (默认23:30)
                      --remove      移除所有定时任务
                      --list        查看任务状态
                      --time HH:MM  指定执行时间
  help                显示帮助

示例:
  python app_usage_tracker.py collect
  python app_usage_tracker.py daily --date 2026-03-19
  python app_usage_tracker.py focus --timer 25
  python app_usage_tracker.py export --weekly
  python app_usage_tracker.py chart --pie
  python app_usage_tracker.py timeout --check
  python app_usage_tracker.py categories add 工作 notion
  python app_usage_tracker.py schedule --setup-all
  python app_usage_tracker.py schedule --list

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
