# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import psutil
import time
from collections import defaultdict

# Initialize CPU measurement (first call returns 0)
psutil.cpu_percent(interval=None)
time.sleep(0.1)
psutil.cpu_percent(interval=None)

# Get all processes
procs_data = []
for p in psutil.process_iter(['name', 'memory_info', 'create_time', 'cpu_percent']):
    try:
        info = p.info
        name = info['name']
        if not name:
            continue
        mem_mb = info['memory_info'].rss / 1024 / 1024 if info.get('memory_info') else 0
        create_time = info.get('create_time')
        cpu = info.get('cpu_percent') or 0
        
        # Calculate duration in minutes if we have create_time
        if create_time:
            duration_min = (time.time() - create_time) / 60
        else:
            duration_min = 0
            
        procs_data.append({
            'name': name,
            'memory_mb': mem_mb,
            'cpu': cpu,
            'duration_min': duration_min
        })
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass

# Aggregate by application name
agg = defaultdict(lambda: {'count': 0, 'total_mem': 0, 'max_cpu': 0, 'max_duration': 0})

for p in procs_data:
    name = p['name']
    agg[name]['count'] += 1
    agg[name]['total_mem'] += p['memory_mb']
    agg[name]['max_cpu'] = max(agg[name]['max_cpu'], p['cpu'])
    agg[name]['max_duration'] = max(agg[name]['max_duration'], p['duration_min'])

# Convert to list and sort by total memory
apps = [
    {
        'name': name,
        'count': data['count'],
        'total_mem': data['total_mem'],
        'max_cpu': data['max_cpu'],
        'max_duration': data['max_duration']
    }
    for name, data in agg.items()
]
apps_sorted = sorted(apps, key=lambda x: x['total_mem'], reverse=True)

# Print report
print("=" * 65)
print("📊 应用使用统计 (按应用汇总)")
print("=" * 65)
print(f"{'应用名称':<28} {'进程数':<6} {'总内存(MB)':<12} {'CPU峰值%':<8} {'最长运行'}")
print("-" * 65)

total_mem = 0
for app in apps_sorted[:15]:
    total_mem += app['total_mem']
    hrs = int(app['max_duration'] // 60)
    mins = int(app['max_duration'] % 60)
    duration_str = f"{hrs}h {mins}m" if hrs > 0 else f"{mins}m"
    print(f"{app['name']:<28} {app['count']:<6} {app['total_mem']:<12.1f} {app['max_cpu']:<8.1f} {duration_str}")

print("-" * 65)
print(f"Top 15 应用内存合计: {total_mem:.1f} MB ({total_mem/1024:.2f} GB)")
print(f"总进程数: {len(procs_data)}")
print("=" * 65)
