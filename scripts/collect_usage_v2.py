# -*- coding: utf-8 -*-
"""
应用使用数据采集脚本 V2
通过 DataStore 写入数据，新增前台检测字段
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import psutil

sys.path.insert(0, str(Path(__file__).parent.parent))
from app_categories import classify_app
from scripts.data_store import DataStore

ROOT_DIR = Path(__file__).parent.parent
CONFIG_FILE = ROOT_DIR / "config.json"


def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"interval_minutes": 60, "top_processes": 50, "exclude_system": True}


def get_process_usage(top_n=50, exclude_system=True, foreground_app=None):
    """
    获取进程使用数据
    Args:
        top_n: 保留的进程数量
        exclude_system: 是否排除系统进程
        foreground_app: 当前前台应用名称（用于标记 is_foreground）
    """
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
            duration_min = (current_time - create_time) / 60 if create_time else 0

            category, _ = classify_app(name)

            if exclude_system and category == "系统":
                continue

            is_fg = 1 if (foreground_app and name.lower() == foreground_app.lower()) else 0

            processes.append({
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'hour': datetime.now().hour,
                'name': name,
                'Name': name,
                'category': category,
                'Category': category,
                'cpu': round(cpu, 2),
                'CPU': round(cpu, 2),
                'memory_mb': round(mem_mb, 2),
                'MemoryMB': round(mem_mb, 2),
                'duration_minutes': round(duration_min, 2),
                'DurationMinutes': round(duration_min, 2),
                'is_foreground': is_fg,
                'foreground_minutes': round(duration_min, 2) if is_fg else 0,
                'device_id': 'local',
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    processes.sort(key=lambda x: x['cpu'], reverse=True)
    return processes[:top_n]


def collect_v2(config=None, foreground_detector=None):
    """
    V2 数据采集：通过 DataStore 写入，支持前台检测
    """
    if config is None:
        config = load_config()

    top_n = config.get('top_processes', 50)
    exclude_system = config.get('exclude_system', True)

    print(f"🕐 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始采集应用使用数据...")

    # 获取前台应用
    fg_app = None
    if foreground_detector:
        fg_info = foreground_detector.get_current_foreground()
        if fg_info:
            fg_app = fg_info.get("app_name")

    processes = get_process_usage(top_n=top_n, exclude_system=exclude_system, foreground_app=fg_app)

    if not processes:
        print("⚠️ 未获取到进程数据")
        return

    print(f"📊 获取到 {len(processes)} 个进程")

    # 通过 DataStore 写入
    today = datetime.now().strftime("%Y-%m-%d")
    store = DataStore()
    store.save_usage_records(processes, today)
    store.close()

    # 显示汇总
    fg_count = sum(1 for p in processes if p.get('is_foreground'))
    print(f"  前台应用: {fg_app or '未检测'} ({fg_count} 条前台记录)")

    stats = defaultdict(lambda: {'duration': 0, 'cpu_peak': 0, 'count': 0, 'category': ''})
    for r in processes:
        name = r.get('name', 'Unknown')
        stats[name]['duration'] += r.get('duration_minutes', 0)
        stats[name]['cpu_peak'] = max(stats[name]['cpu_peak'], r.get('cpu', 0))
        stats[name]['count'] += 1
        stats[name]['category'] = r.get('category', '其他')

    print(f"\n📈 本次采集 Top 5:")
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['duration'], reverse=True)
    for name, stat in sorted_stats[:5]:
        hrs = int(stat['duration'] // 60)
        mins = int(stat['duration'] % 60)
        print(f"  [{stat['category']}] {name:<20} {hrs}h {mins}m, CPU: {stat['cpu_peak']:.1f}%")

    print("\n✅ 采集完成 (V2 DataStore)")


if __name__ == "__main__":
    collect_v2()
