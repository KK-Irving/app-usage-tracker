# -*- coding: utf-8 -*-
"""
周报/月报生成脚本
分析多日趋势，与上周/上月对比
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
REPORT_DIR = DATA_DIR / "reports"


def load_data(date):
    """加载指定日期的数据（优先使用 DataStore）"""
    try:
        from scripts.data_store import DataStore
        store = DataStore()
        records = store.get_usage_records(date)
        store.close()
        if records:
            return {"date": date, "records": records}
    except Exception:
        pass
    data_file = DATA_DIR / f"usage_{date}.json"
    if data_file.exists():
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def get_week_dates():
    """获取本周和上周的日期列表"""
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    this_week = [(week_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    last_week_start = week_start - timedelta(days=7)
    last_week = [(last_week_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    return this_week, last_week


def get_month_dates():
    """获取本月和上月的日期列表"""
    today = datetime.now()

    # 本月: 从1号到今天
    this_month_start = datetime(today.year, today.month, 1)
    this_month_days = (today - this_month_start).days + 1
    this_month = [(this_month_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(this_month_days)]

    # 上月
    if today.month == 1:
        last_month_start = datetime(today.year - 1, 12, 1)
    else:
        last_month_start = datetime(today.year, today.month - 1, 1)
    last_month_end = this_month_start - timedelta(days=1)
    last_month_days = (last_month_end - last_month_start).days + 1
    last_month = [(last_month_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(last_month_days)]

    return this_month, last_month


def aggregate_multi_days(dates):
    """聚合多天数据"""
    all_records = []
    for date in dates:
        data = load_data(date)
        if data and data.get('records'):
            all_records.extend(data['records'])
    return all_records


def analyze_trend(this_data, last_data):
    """
    分析趋势变化
    Returns:
        {'this_total', 'last_total', 'change_pct', 'this_top5', 'last_top5'}
    """
    this_total = len(this_data)
    last_total = len(last_data)

    this_apps = Counter([r.get('Name', 'Unknown') for r in this_data])
    last_apps = Counter([r.get('Name', 'Unknown') for r in last_data])

    return {
        'this_total': this_total,
        'last_total': last_total,
        'change_pct': ((this_total - last_total) / last_total * 100) if last_total > 0 else 0,
        'this_top5': this_apps.most_common(5),
        'last_top5': last_apps.most_common(5)
    }


def generate_weekly_report():
    """生成周报"""
    this_week, last_week = get_week_dates()
    this_data = aggregate_multi_days(this_week)
    last_data = aggregate_multi_days(last_week)

    if not this_data:
        print("❌ 本周暂无数据")
        return None

    trend = analyze_trend(this_data, last_data)
    last_apps_dict = dict(trend['last_top5'])

    report = []
    report.append("=" * 60)
    report.append("📊 周报 - 本周 vs 上周")
    report.append("=" * 60)
    report.append(f"\n📅 本周: {this_week[0]} ~ {this_week[-1]}")
    report.append(f"📅 上周: {last_week[0]} ~ {last_week[-1]}")
    report.append(f"\n📈 数据量: {trend['this_total']} vs {trend['last_total']} ({trend['change_pct']:+.1f}%)")

    report.append("\n🔥 Top 5 应用 (本周):")
    for i, (app, cnt) in enumerate(trend['this_top5'], 1):
        last_cnt = last_apps_dict.get(app, 0)
        change = cnt - last_cnt
        sign = "+" if change > 0 else ""
        report.append(f"   {i}. {app:<25} {cnt:>4} ({sign}{change})")

    if not last_data:
        report.append("\n⚠️ 上周无数据，仅展示本周数据")

    # V2: 目标达成趋势
    try:
        from scripts.data_store import DataStore
        from scripts.goal_manager import GoalManager
        store = DataStore()
        gm = GoalManager(store)
        weekly_goals = gm.evaluate_weekly()
        store.close()
        if weekly_goals:
            report.append("\n🎯 目标达成趋势 (过去7天):")
            for wg in weekly_goals:
                g = wg["goal"]
                days = wg["achievement_days"]
                bar = "".join("✅" if d else "❌" for d in wg["daily_achieved"])
                report.append(f"   {g.target}: {bar} ({days}/7天)")
    except Exception:
        pass

    report_text = "\n".join(report)
    print(report_text)

    # 保存
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORT_DIR / f"weekly_{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_text)
    print(f"\n📄 周报已保存: {report_file}")
    return report_text


def generate_monthly_report():
    """生成月报"""
    this_month, last_month = get_month_dates()
    this_data = aggregate_multi_days(this_month)
    last_data = aggregate_multi_days(last_month)

    if not this_data:
        print("❌ 本月暂无数据")
        return None

    trend = analyze_trend(this_data, last_data)
    last_apps_dict = dict(trend['last_top5'])

    report = []
    report.append("=" * 60)
    report.append("📊 月报 - 本月 vs 上月")
    report.append("=" * 60)
    report.append(f"\n📈 数据量: {trend['this_total']} vs {trend['last_total']} ({trend['change_pct']:+.1f}%)")

    report.append("\n🔥 Top 5 应用 (本月):")
    for i, (app, cnt) in enumerate(trend['this_top5'], 1):
        last_cnt = last_apps_dict.get(app, 0)
        change = cnt - last_cnt
        sign = "+" if change > 0 else ""
        report.append(f"   {i}. {app:<25} {cnt:>5} ({sign}{change})")

    if not last_data:
        report.append("\n⚠️ 上月无数据，仅展示本月数据")

    report_text = "\n".join(report)
    print(report_text)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORT_DIR / f"monthly_{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_text)
    print(f"\n📄 月报已保存: {report_file}")
    return report_text


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='周报/月报生成')
    parser.add_argument('--weekly', action='store_true', help='生成周报')
    parser.add_argument('--monthly', action='store_true', help='生成月报')
    args = parser.parse_args()

    if args.monthly:
        generate_monthly_report()
    else:
        generate_weekly_report()
