# -*- coding: utf-8 -*-
"""
每日使用报告生成器
生成包含时间块分析、专注力追踪、碎片时间的完整报告
"""
import json
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))
from app_categories import classify_app

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
REPORT_DIR = DATA_DIR / "reports"

# 时间块定义
TIME_BLOCKS = {
    "🌙 深夜": (0, 6),
    "🌅 早上": (6, 9),
    "☀️ 上午": (9, 12),
    "🍚 午间": (12, 14),
    "🌤️ 下午": (14, 18),
    "🌆 傍晚": (18, 21),
    "🌃 晚上": (21, 24)
}

BLOCK_ORDER = ["🌙 深夜", "🌅 早上", "☀️ 上午", "🍚 午间", "🌤️ 下午", "🌆 傍晚", "🌃 晚上"]


def get_time_block(hour):
    """将小时转换为时间块名称"""
    for name, (start, end) in TIME_BLOCKS.items():
        if start <= hour < end:
            return name
    return "🌃 晚上"


def load_date_data(date_str):
    """加载指定日期的数据（优先使用 DataStore）"""
    try:
        from scripts.data_store import DataStore
        store = DataStore()
        records = store.get_usage_records(date_str)
        store.close()
        if records:
            return {"date": date_str, "records": records}
    except Exception:
        pass
    # 回退到 JSON 文件
    data_file = DATA_DIR / f"usage_{date_str}.json"
    if data_file.exists():
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def analyze_app_usage(records):
    """分析应用使用情况"""
    app_stats = defaultdict(lambda: {'duration': 0, 'cpu_peak': 0, 'memory': 0, 'count': 0})
    for record in records:
        name = record.get('Name', 'Unknown')
        app_stats[name]['duration'] += record.get('DurationMinutes', 0)
        app_stats[name]['cpu_peak'] = max(app_stats[name]['cpu_peak'], record.get('CPU', 0))
        app_stats[name]['memory'] += record.get('MemoryMB', 0)
        app_stats[name]['count'] += 1
    return app_stats


def analyze_category_usage(records):
    """分析分类使用情况（使用统一分类引擎）"""
    category_stats = defaultdict(lambda: {'duration': 0, 'apps': set(), 'count': 0})
    for record in records:
        name = record.get('Name', 'Unknown')
        category, _ = classify_app(name)
        duration = record.get('DurationMinutes', 0)
        category_stats[category]['duration'] += duration
        category_stats[category]['apps'].add(name)
        category_stats[category]['count'] += 1
    return category_stats


def analyze_time_blocks(records):
    """分析时间块分布，标记高效/低效时段"""
    block_stats = defaultdict(lambda: {
        'total': 0, 'apps': Counter(), 'duration': 0,
        'category_duration': defaultdict(float)
    })
    for record in records:
        hour = record.get('hour', 0)
        block = get_time_block(hour)
        name = record.get('Name', 'Unknown')
        duration = record.get('DurationMinutes', 0)
        category, _ = classify_app(name)

        block_stats[block]['total'] += 1
        block_stats[block]['apps'][name] += 1
        block_stats[block]['duration'] += duration
        block_stats[block]['category_duration'][category] += duration

    # 标记高效/低效
    for block, data in block_stats.items():
        total_dur = data['duration']
        if total_dur == 0:
            data['efficiency'] = "—"
            continue
        work_dev = data['category_duration'].get('工作', 0) + data['category_duration'].get('开发', 0)
        social_ent = data['category_duration'].get('社交', 0) + data['category_duration'].get('娱乐', 0)
        work_ratio = work_dev / total_dur
        social_ratio = social_ent / total_dur
        if work_ratio > 0.6:
            data['efficiency'] = "🟢 高效时段"
        elif social_ratio > 0.5:
            data['efficiency'] = "🔴 低效时段"
        else:
            data['efficiency'] = "🟡 一般"

    return block_stats


def analyze_focus_time(records, threshold_min=30):
    """分析专注时间"""
    sorted_records = sorted(records, key=lambda x: x.get('timestamp', ''))
    focus_sessions = []
    current_session = None

    for record in sorted_records:
        name = record.get('Name', 'Unknown')
        duration = record.get('DurationMinutes', 0)
        category, _ = classify_app(name)

        if category not in ['工作', '开发']:
            if current_session and current_session['duration'] >= threshold_min:
                focus_sessions.append(current_session)
            current_session = None
            continue

        if current_session is None or current_session['app'] != name:
            if current_session and current_session['duration'] >= threshold_min:
                focus_sessions.append(current_session)
            current_session = {'app': name, 'duration': duration, 'category': category}
        else:
            current_session['duration'] += duration

    if current_session and current_session['duration'] >= threshold_min:
        focus_sessions.append(current_session)

    return focus_sessions


def analyze_fragment_time(records, threshold_max=10):
    """分析碎片时间"""
    app_sessions = defaultdict(list)
    for record in records:
        name = record.get('Name', 'Unknown')
        duration = record.get('DurationMinutes', 0)
        if duration <= threshold_max:
            app_sessions[name].append(duration)

    total_records = len(records)
    fragment_records = sum(len(s) for s in app_sessions.values())
    return {
        'total_records': total_records,
        'fragment_records': fragment_records,
        'fragment_ratio': fragment_records / total_records if total_records > 0 else 0,
        'fragment_apps': dict(sorted(app_sessions.items(), key=lambda x: len(x[1]), reverse=True)[:10])
    }


def detect_idle_time(records):
    """检测空闲时间"""
    hourly_activity = defaultdict(int)
    for record in records:
        ts = record.get('timestamp', '')
        if ts:
            try:
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                hourly_activity[dt.hour] += 1
            except ValueError:
                pass

    idle_hours = [h for h, c in hourly_activity.items() if c < 5]
    return {
        'idle_hours': sorted(idle_hours),
        'total_idle_hours': len(idle_hours),
        'hourly_activity': dict(hourly_activity)
    }


def generate_suggestions(category_stats, focus_sessions):
    """基于数据生成改进建议"""
    suggestions = []
    total_duration = sum(c['duration'] for c in category_stats.values())
    if total_duration == 0:
        return suggestions

    work_dur = category_stats.get('工作', {}).get('duration', 0)
    dev_dur = category_stats.get('开发', {}).get('duration', 0)
    social_dur = category_stats.get('社交', {}).get('duration', 0)
    ent_dur = category_stats.get('娱乐', {}).get('duration', 0)

    work_ratio = (work_dur + dev_dur) / total_duration * 100
    if work_ratio > 60:
        suggestions.append(f"✅ 工作效率较高，工作/开发时间占比 {work_ratio:.1f}%")
    elif work_ratio < 30:
        suggestions.append(f"⚠️ 工作/开发时间占比仅 {work_ratio:.1f}%，建议增加专注时间")

    if social_dur > ent_dur * 2:
        suggestions.append("⚠️ 社交应用使用时间较长，注意适当休息")

    total_focus = sum(s['duration'] for s in focus_sessions)
    if total_focus < 120:
        suggestions.append("💪 建议增加连续专注时间，可尝试番茄工作法")

    return suggestions


def generate_report(date_str=None):
    """生成每日报告"""
    if date_str:
        data = load_date_data(date_str)
        report_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y年%m月%d日")
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
        data = load_date_data(date_str)
        report_date = datetime.now().strftime("%Y年%m月%d日")

    if not data or not data.get('records'):
        print(f"❌ 没有找到 {report_date} 的数据")
        print("提示: 请先运行定时采集任务收集数据")
        return None

    records = data['records']
    app_stats = analyze_app_usage(records)
    category_stats = analyze_category_usage(records)
    block_stats = analyze_time_blocks(records)
    focus_sessions = analyze_focus_time(records)
    fragment_data = analyze_fragment_time(records)
    idle_data = detect_idle_time(records)
    suggestions = generate_suggestions(category_stats, focus_sessions)

    report = []
    report.append("=" * 70)
    report.append(f"📊 应用使用日报 - {report_date}")
    report.append("=" * 70)

    # 1. 总览
    total_duration = sum(s['duration'] for s in app_stats.values())
    total_hours = total_duration / 60
    report.append(f"\n🕐 总使用时长: {int(total_hours)}h {int(total_duration % 60)}m")
    report.append(f"📝 记录总数: {len(records)} 条")
    report.append(f"📱 应用数量: {len(app_stats)} 个")

    # 2. 分类汇总
    report.append("\n" + "=" * 70)
    report.append("📈 分类使用情况")
    report.append("=" * 70)
    sorted_cat = sorted(category_stats.items(), key=lambda x: x[1]['duration'], reverse=True)
    total_cat_duration = sum(c['duration'] for _, c in sorted_cat)
    for cat, cat_data in sorted_cat:
        pct = cat_data['duration'] / total_cat_duration * 100 if total_cat_duration > 0 else 0
        hrs = int(cat_data['duration'] // 60)
        mins = int(cat_data['duration'] % 60)
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        report.append(f"{cat:<6} {bar} {pct:5.1f}%  {hrs}h {mins}m ({len(cat_data['apps'])}个应用)")

    # 3. Top 10 应用
    report.append("\n" + "=" * 70)
    report.append("🏆 Top 10 应用 (按使用时长)")
    report.append("=" * 70)
    report.append(f"{'应用名称':<25} {'分类':<6} {'时长':<12} {'CPU峰值':<10} {'内存MB'}")
    report.append("-" * 70)
    sorted_apps = sorted(app_stats.items(), key=lambda x: x[1]['duration'], reverse=True)[:10]
    for name, stat in sorted_apps:
        hrs = int(stat['duration'] // 60)
        mins = int(stat['duration'] % 60)
        cat, _ = classify_app(name)
        report.append(f"{name:<25} {cat:<6} {hrs}h {mins}m      {stat['cpu_peak']:<10.1f} {stat['memory']:.0f}")

    # 4. 时间块分布
    report.append("\n" + "=" * 70)
    report.append("🕐 时间块分布")
    report.append("=" * 70)
    for block in BLOCK_ORDER:
        if block in block_stats:
            bd = block_stats[block]
            hrs = int(bd['duration'] // 60)
            mins = int(bd['duration'] % 60)
            top_apps = bd['apps'].most_common(3)
            app_str = ", ".join([f"{a}({c})" for a, c in top_apps])
            # 进度条
            max_total = max((block_stats[b]['total'] for b in block_stats), default=1)
            bar_len = int(bd['total'] / max_total * 20) if max_total > 0 else 0
            bar = "█" * bar_len + "░" * (20 - bar_len)
            report.append(f"\n{block} {bd['efficiency']} ({hrs}h {mins}m)")
            report.append(f"  {bar} 活跃记录: {bd['total']} | {app_str}")

    # 5. 专注力分析
    report.append("\n" + "=" * 70)
    report.append("🎯 专注力分析 (>=30分钟连续使用)")
    report.append("=" * 70)
    if focus_sessions:
        total_focus = sum(s['duration'] for s in focus_sessions)
        report.append(f"专注总时长: {int(total_focus/60)}h {int(total_focus%60)}m ({len(focus_sessions)}次)")
        for i, s in enumerate(sorted(focus_sessions, key=lambda x: x['duration'], reverse=True)[:5], 1):
            report.append(f"  {i}. {s['app']:<20} {int(s['duration']//60)}h {int(s['duration']%60)}m [{s['category']}]")
    else:
        report.append("未检测到专注时段 (需要更多数据)")

    # 6. 碎片时间分析
    report.append("\n" + "=" * 70)
    report.append("⏱️ 碎片时间分析 (<=10分钟)")
    report.append("=" * 70)
    report.append(f"碎片记录: {fragment_data['fragment_records']}/{fragment_data['total_records']} ({fragment_data['fragment_ratio']*100:.1f}%)")
    if fragment_data['fragment_apps']:
        report.append("\n碎片时间主要分布:")
        for app, durations in list(fragment_data['fragment_apps'].items())[:5]:
            report.append(f"  - {app}: {len(durations)}次")

    # 7. 空闲时间检测
    report.append("\n" + "=" * 70)
    report.append("💤 空闲时间检测")
    report.append("=" * 70)
    if idle_data['idle_hours']:
        report.append(f"低活跃时段: {', '.join(f'{h:02d}:00' for h in idle_data['idle_hours'])}")
        report.append(f"共 {idle_data['total_idle_hours']} 个小时")
    else:
        report.append("未检测到明显空闲时段")

    # 8. 建议（V2: 使用 SuggestionEngine）
    report.append("\n" + "=" * 70)
    report.append("💡 建议")
    report.append("=" * 70)
    try:
        from scripts.data_store import DataStore
        from scripts.suggestion_engine import SuggestionEngine
        store = DataStore()
        engine = SuggestionEngine(store)
        v2_suggestions = engine.get_suggestions_or_fallback()
        store.close()
        for s in v2_suggestions:
            report.append(f"  [{s.type}] {s.content}" + (f" (置信度: {s.confidence}%)" if s.confidence > 0 else ""))
    except Exception:
        if suggestions:
            for s in suggestions:
                report.append(s)
        else:
            report.append("暂无建议，继续保持！")

    # 9. V2: 目标达成率
    try:
        from scripts.data_store import DataStore
        from scripts.goal_manager import GoalManager
        store = DataStore()
        gm = GoalManager(store)
        goal_results = gm.evaluate(date_str)
        store.close()
        if goal_results:
            report.append("\n" + "=" * 70)
            report.append("🎯 目标达成率")
            report.append("=" * 70)
            for r in goal_results:
                g = r["goal"]
                status = "✅ 达成" if r["achieved"] else "❌ 未达成"
                type_label = "≥" if g.goal_type == "min" else "≤"
                report.append(f"  {g.target} ({type_label}{int(g.minutes)}min): "
                              f"实际 {int(r['actual_minutes'])}min, "
                              f"达成率 {r['achievement_rate']:.0f}% {status}")
    except Exception:
        pass

    # 10. V2: 切换分析
    try:
        from scripts.data_store import DataStore
        from scripts.switch_analyzer import SwitchAnalyzer
        store = DataStore()
        sa = SwitchAnalyzer(store)
        hourly = sa.get_hourly_switch_counts(date_str)
        cost = sa.get_context_switch_cost(date_str)
        top_pairs = sa.get_top_switch_pairs(date_str)
        store.close()
        if hourly:
            report.append("\n" + "=" * 70)
            report.append("🔄 应用切换分析")
            report.append("=" * 70)
            total_switches = sum(hourly.values())
            report.append(f"  总切换次数: {total_switches}")
            report.append(f"  上下文切换成本: {cost:.0f} 分钟")
            if top_pairs:
                report.append("  Top 切换对:")
                for f_app, t_app, cnt in top_pairs[:5]:
                    report.append(f"    {f_app} ↔ {t_app}: {cnt} 次")
    except Exception:
        pass

    # 11. V2: 项目时间分布
    try:
        from scripts.data_store import DataStore
        from scripts.project_tracker import ProjectTracker
        store = DataStore()
        pt = ProjectTracker(store)
        proj_report = pt.get_project_report(date_str)
        store.close()
        if proj_report:
            report.append("\n" + "=" * 70)
            report.append("📁 项目时间分布")
            report.append("=" * 70)
            for p in proj_report:
                hrs = int(p["minutes"] // 60)
                mins = int(p["minutes"] % 60)
                report.append(f"  {p['name']:<20} {hrs}h {mins}m ({p['pct']:.1f}%)")
    except Exception:
        pass

    # 12. V2: 前台/后台时间
    fg_total = sum(r.get("foreground_minutes", 0) for r in records)
    bg_total = total_duration - fg_total
    if fg_total > 0:
        report.append("\n" + "=" * 70)
        report.append("🖥️ 前台/后台时间")
        report.append("=" * 70)
        report.append(f"  前台活跃: {int(fg_total//60)}h {int(fg_total%60)}m")
        report.append(f"  后台运行: {int(bg_total//60)}h {int(bg_total%60)}m")

    report.append("\n" + "=" * 70)
    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description='生成应用使用日报')
    parser.add_argument('--date', '-d', type=str, help='指定日期 (YYYY-MM-DD)')
    parser.add_argument('--output', '-o', type=str, help='输出文件路径')
    args = parser.parse_args()

    report = generate_report(args.date)
    if report:
        print(report)
        date_str = args.date or datetime.now().strftime("%Y-%m-%d")
        output_path = Path(args.output) if args.output else REPORT_DIR / f"daily_{date_str}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n✅ 报告已保存到: {output_path}")
    return report


if __name__ == "__main__":
    main()
