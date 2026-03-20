# -*- coding: utf-8 -*-
"""
应用使用数据采集脚本 v2.0
支持：定时采集、应用分类、时间块分析、专注力追踪
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter

# Setup UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')

# Data directory
DATA_DIR = Path("E:/qclaw/workspace/skills/app-usage-tracker/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Load config
CONFIG_FILE = Path("E:/qclaw/workspace/skills/app-usage-tracker/config.json")
if CONFIG_FILE.exists():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        CONFIG = json.load(f)
else:
    CONFIG = {
        "app_categories": {},
        "focus_apps": [],
        "fragment_time_threshold_minutes": 5
    }


def get_process_usage():
    """获取进程使用数据"""
    import psutil
    
    processes = []
    current_time = time.time()
    
    for p in psutil.process_iter(['name', 'memory_info', 'create_time', 'cpu_percent']):
        try:
            info = p.info
            name = info['name']
            if not name:
                continue
            
            mem_mb = info['memory_info'].rss / 1024 / 1024 if info.get('memory_info') else 0
            create_time = info.get('create_time')
            cpu = info.get('cpu_percent') or 0
            
            # Calculate duration
            if create_time:
                duration_min = (current_time - create_time) / 60
            else:
                duration_min = 0
            
            # Get category
            category = get_app_category(name)
            
            processes.append({
                'Name': name,
                'Category': category,
                'CPU': round(cpu, 2),
                'MemoryMB': round(mem_mb, 2),
                'DurationMinutes': round(duration_min, 2),
                'CreateTime': create_time
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    return processes


def get_app_category(app_name):
    """获取应用分类"""
    app_name_lower = app_name.lower()
    categories = CONFIG.get("app_categories", {})
    
    for category, apps in categories.items():
        if any(app.lower() in app_name_lower for app in apps):
            return category
    return "其他"


def load_today_data():
    """加载今天的已有数据"""
    today = datetime.now().strftime("%Y-%m-%d")
    data_file = DATA_DIR / f"usage_{today}.json"
    
    if data_file.exists():
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"date": today, "records": []}


def save_today_data(data):
    """保存今天的数据"""
    today = datetime.now().strftime("%Y-%m-%d")
    data_file = DATA_DIR / f"usage_{today}.json"
    
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def aggregate_stats(records):
    """汇总统计数据"""
    stats = defaultdict(lambda: {
        'name': '',
        'category': '其他',
        'total_duration_min': 0,
        'cpu_peak': 0,
        'memory_total_mb': 0,
        'active_count': 0
    })
    
    for record in records:
        name = record.get('Name', 'Unknown')
        category = record.get('Category', '其他')
        
        stats[name]['name'] = name
        stats[name]['category'] = category
        stats[name]['total_duration_min'] += record.get('DurationMinutes', 0)
        stats[name]['cpu_peak'] = max(stats[name]['cpu_peak'], record.get('CPU', 0))
        stats[name]['memory_total_mb'] += record.get('MemoryMB', 0)
        stats[name]['active_count'] += 1
    
    return dict(stats)


def analyze_time_blocks(records):
    """分析时间块分布"""
    time_blocks = {
        "🌙 深夜 (0-6点)": list(range(0, 6)),
        "🌅 早上 (6-9点)": list(range(6, 9)),
        "☀️ 上午 (9-12点)": list(range(9, 12)),
        "🍚 午间 (12-14点)": list(range(12, 14)),
        "🌤️ 下午 (14-18点)": list(range(14, 18)),
        "🌆 傍晚 (18-21点)": list(range(18, 21)),
        "🌃 晚上 (21-24点)": list(range(21, 24))
    }
    
    block_data = {block: {'count': 0, 'apps': []} for block in time_blocks}
    
    for record in records:
        hour = record.get('hour', 0)
        name = record.get('Name', '')
        
        for block_name, hours in time_blocks.items():
            if hour in hours:
                block_data[block_name]['count'] += 1
                block_data[block_name]['apps'].append(name)
                break
    
    # Calculate percentages
    total = len(records)
    result = {}
    for block_name, data in block_data.items():
        if total > 0:
            pct = data['count'] / total * 100
        else:
            pct = 0
        # Get top apps for this block
        app_counts = Counter(data['apps'])
        top_apps = app_counts.most_common(3)
        result[block_name] = {
            'count': data['count'],
            'percentage': round(pct, 1),
            'top_apps': top_apps
        }
    
    return result


def analyze_focus_time(records):
    """分析专注时间"""
    focus_apps = CONFIG.get("focus_apps", [])
    
    # Group by hour
    hourly_focus = defaultdict(lambda: {'total': 0, 'focus': 0})
    
    for record in records:
        hour = record.get('hour', 0)
        name = record.get('Name', '')
        duration = record.get('DurationMinutes', 0)
        
        hourly_focus[hour]['total'] += duration
        if any(focus.lower() in name.lower() for focus in focus_apps):
            hourly_focus[hour]['focus'] += duration
    
    # Calculate focus percentage per hour
    focus_analysis = {}
    for hour, data in hourly_focus.items():
        total = data['total']
        focus = data['focus']
        if total > 0:
            pct = focus / total * 100
        else:
            pct = 0
        focus_analysis[hour] = {
            'total_minutes': round(total, 1),
            'focus_minutes': round(focus, 1),
            'focus_percentage': round(pct, 1)
        }
    
    return focus_analysis


def analyze_fragment_time(records):
    """分析碎片时间"""
    threshold = CONFIG.get("fragment_time_threshold_minutes", 5)
    
    # Group by hour
    hourly_data = defaultdict(list)
    for record in records:
        hour = record.get('hour', 0)
        duration = record.get('DurationMinutes', 0)
        hourly_data[hour].append(duration)
    
    fragment_analysis = {}
    for hour, durations in hourly_data.items():
        total = sum(durations)
        fragment = sum(1 for d in durations if d < threshold)
        if durations:
            pct = fragment / len(durations) * 100
        else:
            pct = 0
        
        fragment_analysis[hour] = {
            'total_sessions': len(durations),
            'fragment_sessions': fragment,
            'fragment_percentage': round(pct, 1)
        }
    
    return fragment_analysis


def collect():
    """执行数据采集"""
    print(f"🕐 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始采集...")
    
    # Get current process data
    processes = get_process_usage()
    
    if not processes:
        print("⚠️ 未获取到进程数据")
        return
    
    print(f"📊 获取到 {len(processes)} 个进程")
    
    # Load existing data
    data = load_today_data()
    
    # Add new records
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hour = datetime.now().hour
    
    for proc in processes:
        record = {
            'timestamp': timestamp,
            'hour': hour,
            **proc
        }
        # Remove CreateTime from record (not JSON serializable)
        record.pop('CreateTime', None)
        data['records'].append(record)
    
    # Save data
    save_today_data(data)
    
    # Generate daily report
    generate_daily_report(data)
    
    print("\n✅ 采集完成")


def generate_daily_report(data):
    """生成每日报告"""
    records = data.get('records', [])
    if not records:
        return
    
    # Stats
    stats = aggregate_stats(records)
    
    # Time blocks
    time_blocks = analyze_time_blocks(records)
    
    # Focus time
    focus_time = analyze_focus_time(records)
    
    # Fragment time
    fragment_time = analyze_fragment_time(records)
    
    # Print report
    print("\n" + "="*60)
    print(f"📊 每日使用报告 - {data['date']}")
    print("="*60)
    
    # Category summary
    category_stats = defaultdict(lambda: {'count': 0, 'duration': 0})
    for name, stat in stats.items():
        cat = stat['category']
        category_stats[cat]['count'] += 1
        category_stats[cat]['duration'] += stat['total_duration_min']
    
    print("\n📂 应用分类统计:")
    for cat, s in sorted(category_stats.items(), key=lambda x: x[1]['duration'], reverse=True):
        hrs = int(s['duration'] // 60)
        mins = int(s['duration'] % 60)
        print(f"   {cat}: {s['count']}个应用, 累计 {hrs}h {mins}m")
    
    # Top apps
    print("\n🔥 Top 10 应用 (按使用时长):")
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['total_duration_min'], reverse=True)
    for i, (name, stat) in enumerate(sorted_stats[:10], 1):
        hrs = int(stat['total_duration_min'] // 60)
        mins = int(stat['total_duration_min'] % 60)
        print(f"   {i:2}. {name:<25} [{stat['category']:<4}] {hrs}h {mins}m")
    
    # Time blocks
    print("\n🕐 时间块分布:")
    for block, info in time_blocks.items():
        if info['count'] > 0:
            top_str = ', '.join([f"{app}({cnt})" for app, cnt in info['top_apps']])
            print(f"   {block:<20} {info['percentage']:>5.1f}% ({info['count']}条) - {top_str}")
    
    # Focus time
    print("\n🎯 专注时间分析:")
    for hour in sorted(focus_time.keys()):
        info = focus_time[hour]
        bar = "█" * int(info['focus_percentage']/10) + "░" * (10 - int(info['focus_percentage']/10))
        print(f"   {hour:02d}:00 {bar} {info['focus_percentage']:>5.1f}% 专注 ({info['focus_minutes']:.0f}m / {info['total_minutes']:.0f}m)")
    
    # Fragment time
    print("\n⏱️ 碎片时间分析:")
    for hour in sorted(fragment_time.keys()):
        info = fragment_time[hour]
        if info['fragment_sessions'] > 0:
            print(f"   {hour:02d}:00 {info['fragment_sessions']}/{info['total_sessions']} 会话碎片化 ({info['fragment_percentage']:.0f}%)")
    
    # Save report
    reports_dir = DATA_DIR / "reports"
    reports_dir.mkdir(exist_ok=True)
    report_file = reports_dir / f"daily_{data['date']}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# 📊 每日使用报告 - {data['date']}\n\n")
        f.write(f"总记录数: {len(records)}\n\n")
        f.write("## 应用分类\n")
        for cat, s in sorted(category_stats.items(), key=lambda x: x[1]['duration'], reverse=True):
            f.write(f"- {cat}: {s['count']}个应用, 累计 {int(s['duration']//60)}h {int(s['duration']%60)}m\n")
        f.write("\n## Top 应用\n")
        for i, (name, stat) in enumerate(sorted_stats[:10], 1):
            f.write(f"{i}. {name} [{stat['category']}] {int(stat['total_duration_min']//60)}h {int(stat['total_duration_min']%60)}m\n")
        f.write("\n## 时间块\n")
        for block, info in time_blocks.items():
            if info['count'] > 0:
                f.write(f"- {block}: {info['percentage']}%\n")
        f.write("\n## 专注时间\n")
        for hour in sorted(focus_time.keys()):
            info = focus_time[hour]
            f.write(f"- {hour}:00 - {info['focus_percentage']}% 专注\n")
    
    print(f"\n📄 报告已保存: {report_file}")


if __name__ == "__main__":
    collect()
