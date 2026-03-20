# -*- coding: utf-8 -*-
"""
应用使用数据采集脚本 (增强版)
每小时执行一次，采集当前运行的应用程序数据
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import psutil

# 确保能导入根目录模块
sys.path.insert(0, str(Path(__file__).parent.parent))
from app_categories import classify_app

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
CONFIG_FILE = ROOT_DIR / "config.json"


def load_config():
    """加载全局配置"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"interval_minutes": 60, "top_processes": 50, "exclude_system": True}


def get_process_usage(top_n=50, exclude_system=True):
    """
    获取进程使用数据
    Args:
        top_n: 保留的进程数量
        exclude_system: 是否排除系统进程
    Returns:
        Usage_Record 列表
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

            processes.append({
                'Name': name,
                'Category': category,
                'CPU': round(cpu, 2),
                'MemoryMB': round(mem_mb, 2),
                'DurationMinutes': round(duration_min, 2)
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # 按 CPU 使用率排序，取 top_n
    processes.sort(key=lambda x: x['CPU'], reverse=True)
    return processes[:top_n]


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
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    data_file = DATA_DIR / f"usage_{today}.json"
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def collect(config=None):
    """
    执行一次数据采集
    Args:
        config: 可选配置覆盖，默认从 config.json 读取
    """
    if config is None:
        config = load_config()

    top_n = config.get('top_processes', 50)
    exclude_system = config.get('exclude_system', True)

    print(f"🕐 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始采集应用使用数据...")

    processes = get_process_usage(top_n=top_n, exclude_system=exclude_system)

    if not processes:
        print("⚠️ 未获取到进程数据")
        return

    print(f"📊 获取到 {len(processes)} 个进程")

    data = load_today_data()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hour = datetime.now().hour

    for proc in processes:
        record = {'timestamp': timestamp, 'hour': hour, **proc}
        data['records'].append(record)

    save_today_data(data)

    # 显示汇总
    stats = defaultdict(lambda: {'duration': 0, 'cpu_peak': 0, 'count': 0, 'category': ''})
    for r in data['records']:
        name = r.get('Name', 'Unknown')
        stats[name]['duration'] += r.get('DurationMinutes', 0)
        stats[name]['cpu_peak'] = max(stats[name]['cpu_peak'], r.get('CPU', 0))
        stats[name]['count'] += 1
        stats[name]['category'] = r.get('Category', '其他')

    print(f"\n📈 今日累计 ({len(data['records'])} 条记录):")
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['duration'], reverse=True)
    for name, stat in sorted_stats[:5]:
        hrs = int(stat['duration'] // 60)
        mins = int(stat['duration'] % 60)
        print(f"  [{stat['category']}] {name:<20} {hrs}h {mins}m, CPU: {stat['cpu_peak']:.1f}%")

    print("\n✅ 采集完成")


if __name__ == "__main__":
    collect()
