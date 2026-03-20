# -*- coding: utf-8 -*-
"""
碎片时间分析器
识别短时间使用，统计碎片时间分布
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter

sys.path.insert(0, str(Path(__file__).parent.parent))
from app_categories import classify_app

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
CONFIG_FILE = ROOT_DIR / "config.json"


def load_config():
    """加载配置"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"fragment_time_threshold_minutes": 5}


def load_date_data(date_str):
    """加载指定日期数据"""
    data_file = DATA_DIR / f"usage_{date_str}.json"
    if data_file.exists():
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def analyze_fragments(records, short_threshold=10, medium_threshold=30):
    """
    分析碎片时间
    - 短碎片: < short_threshold 分钟
    - 中碎片: short_threshold ~ medium_threshold 分钟
    - 长使用: > medium_threshold 分钟
    """
    app_hours = defaultdict(set)
    app_counts = defaultdict(int)

    for record in records:
        app = record.get('Name', 'Unknown')
        hour = record.get('hour', 0)
        app_hours[app].add(hour)
        app_counts[app] += 1

    fragments = {'short': [], 'medium': [], 'long': []}

    for app, hours in app_hours.items():
        category, icon = classify_app(app)
        if category == '系统':
            continue

        total_duration = sum(
            r.get('DurationMinutes', 0) for r in records if r.get('Name') == app
        )

        info = {
            'app': app, 'icon': icon, 'category': category,
            'hours': sorted(hours), 'occurrences': app_counts[app],
            'total_duration': total_duration, 'unique_hours': len(hours)
        }

        if total_duration < short_threshold:
            fragments['short'].append(info)
        elif total_duration < medium_threshold:
            fragments['medium'].append(info)
        else:
            fragments['long'].append(info)

    return fragments


def calculate_fragment_stats(records):
    """
    计算碎片化统计
    碎片化指数 = 活跃小时数 / 总记录数
    """
    if not records:
        return {'active_hours': 0, 'total_records': 0, 'fragmentation_index': 0, 'avg_records_per_hour': 0}

    hourly_activity = Counter()
    for record in records:
        hourly_activity[record.get('hour', 0)] += 1

    active_hours = len(hourly_activity)
    total_records = len(records)
    fragmentation_index = active_hours / total_records if total_records > 0 else 0

    return {
        'active_hours': active_hours,
        'total_records': total_records,
        'fragmentation_index': round(fragmentation_index, 3),
        'avg_records_per_hour': round(total_records / 24, 1)
    }


def suggest_fragments_tasks(fragments):
    """基于碎片时间推荐任务"""
    suggestions = []
    if fragments['short']:
        suggestions.append({
            'type': '⚡ 短碎片 (<10分钟)',
            'tasks': ['回复消息', '查看邮件', '浏览资讯', '简单查询'],
            'apps': [f['app'] for f in fragments['short'][:3]]
        })
    if fragments['medium']:
        suggestions.append({
            'type': '⏰ 中碎片 (10-30分钟)',
            'tasks': ['编写文档', '处理工单', '简短会议', '代码 review'],
            'apps': [f['app'] for f in fragments['medium'][:3]]
        })
    return suggestions


def generate_fragment_report(date_str=None):
    """生成碎片时间报告"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    data = load_date_data(date_str)
    if not data:
        print(f"❌ {date_str} 暂无数据，请先运行采集")
        return

    records = data.get('records', [])
    fragments = analyze_fragments(records)
    stats = calculate_fragment_stats(records)
    suggestions = suggest_fragments_tasks(fragments)

    print("=" * 65)
    print("⏱️ 碎片时间分析")
    print("=" * 65)

    print("\n📊 碎片化程度")
    print("-" * 65)
    print(f"  活跃小时数: {stats['active_hours']}/24")
    print(f"  记录总数: {stats['total_records']}")
    print(f"  碎片化指数: {stats['fragmentation_index']:.3f}")
    print(f"  每小时平均记录: {stats['avg_records_per_hour']}")

    print("\n📦 碎片分布")
    print("-" * 65)

    if fragments['short']:
        print("  ⚡ 短碎片应用 (<10分钟):")
        for f in sorted(fragments['short'], key=lambda x: x['total_duration'])[:5]:
            print(f"    {f['icon']} {f['app']:<20} {f['total_duration']:.0f}分钟 ({f['occurrences']}次)")

    if fragments['medium']:
        print("\n  ⏰ 中碎片应用 (10-30分钟):")
        for f in sorted(fragments['medium'], key=lambda x: -x['total_duration'])[:5]:
            print(f"    {f['icon']} {f['app']:<20} {f['total_duration']:.0f}分钟 ({f['occurrences']}次)")

    if fragments['long']:
        print("\n  🔵 长时间使用应用 (>30分钟):")
        for f in sorted(fragments['long'], key=lambda x: -x['total_duration'])[:5]:
            hrs = int(f['total_duration'] // 60)
            mins = int(f['total_duration'] % 60)
            dur = f"{hrs}h {mins}m" if hrs > 0 else f"{mins}m"
            print(f"    {f['icon']} {f['app']:<20} {dur} ({f['occurrences']}次)")

    if suggestions:
        print("\n💡 碎片时间利用建议")
        print("-" * 65)
        for sugg in suggestions:
            print(f"  {sugg['type']}:")
            for task in sugg['tasks'][:3]:
                print(f"    • {task}")

    print("=" * 65)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='碎片时间分析')
    parser.add_argument('--date', type=str, help='指定日期 (YYYY-MM-DD)')
    args = parser.parse_args()
    generate_fragment_report(args.date)
