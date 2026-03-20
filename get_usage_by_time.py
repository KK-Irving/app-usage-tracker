# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import psutil
import time
from datetime import datetime
from collections import defaultdict, Counter

# Get current foreground window info using PowerShell
def get_foreground_apps():
    """获取当前前台应用和活跃窗口"""
    import subprocess
    
    ps_script = """
    Add-Type @"
    using System;
    using System.Runtime.InteropServices;
    using System.Text;
    public class Win32 {
        [DllImport("user32.dll")]
        public static extern IntPtr GetForegroundWindow();
        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
        [DllImport("user32.dll")]
        public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
    }
"@
    $hwnd = [Win32]::GetForegroundWindow()
    $pid = 0
    [Win32]::GetWindowThreadProcessId($hwnd, [ref]$pid) | Out-Null
    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($proc) {
        [PSCustomObject]@{
            ProcessName = $proc.ProcessName
            WindowTitle = (Get-Process -Id $pid).MainWindowTitle
            PID = $pid
        } | ConvertTo-Json
    }
    """
    
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            import json
            data = json.loads(result.stdout.strip())
            return data
    except Exception as e:
        pass
    return None

# Get all processes with window titles
def get_active_windowed_processes():
    """获取所有有窗口的进程"""
    active_apps = defaultdict(lambda: {'count': 0, 'windows': set(), 'first_seen': time.time(), 'last_seen': 0})
    
    current_time = time.time()
    
    for p in psutil.process_iter(['name', 'memory_info', 'create_time', 'cpu_percent']):
        try:
            info = p.info
            name = info['name']
            if not name:
                continue
                
            # Get window title if available
            try:
                window_title = p.info.get('name')  # fallback to process name
            except:
                window_title = None
            
            # Mark as active (seen now)
            active_apps[name]['count'] += 1
            active_apps[name]['last_seen'] = current_time
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    return active_apps

# Build hourly distribution from current snapshot
def get_hourly_distribution():
    """获取按小时分布的应用使用情况"""
    from collections import Counter
    
    current_hour = datetime.now().hour
    
    # For each hour (0-23), we'll show distribution
    # Since we don't have historical data, we'll show current snapshot as "今日活跃"
    
    # Get process info with more details
    procs_info = []
    for p in psutil.process_iter(['name', 'create_time', 'cpu_percent']):
        try:
            info = p.info
            name = info['name']
            if not name:
                continue
                
            create_time = info.get('create_time')
            if create_time:
                proc_hour = datetime.fromtimestamp(create_time).hour
            else:
                proc_hour = current_hour
                
            procs_info.append({
                'name': name,
                'hour': proc_hour,
                'cpu': info.get('cpu_percent') or 0
            })
        except:
            pass
    
    # Group by hour
    hourly_data = defaultdict(list)
    for proc in procs_info:
        hourly_data[proc['hour']].append(proc['name'])
    
    return hourly_data

# Main report
print("=" * 70)
print(f"📊 应用使用时间段分析 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 70)

# Get hourly distribution
hourly_data = get_hourly_distribution()

print("\n🕐 各时间段应用分布 (按进程数统计):\n")

for hour in sorted(hourly_data.keys(), reverse=True)[:6]:  # Last 6 active hours
    apps = hourly_data[hour]
    app_counts = Counter(apps)
    total = len(apps)
    
    print(f"📌 {hour:02d}:00 - {hour:02d}:59 ({total} 进程活跃)")
    
    # Show top apps for this hour
    for app_name, count in app_counts.most_common(5):
        pct = (count / total * 100) if total > 0 else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"   {app_name:<25} {bar} {pct:5.1f}% ({count})")
    print()

# Current active (foreground) app
print("\n🎯 当前前台应用:")
fg = get_foreground_apps()
if fg:
    print(f"   进程: {fg.get('ProcessName', 'N/A')}")
    print(f"   窗口: {fg.get('WindowTitle', 'N/A')[:50]}")
else:
    print("   (无法获取)")

# Summary by time blocks
print("\n📈 时间块分布 (今日):")
print("-" * 70)

# Define time blocks
blocks = {
    "🌙 深夜 (0-6点)": list(range(0, 6)),
    "🌅 早上 (6-9点)": list(range(6, 9)),
    "☀️ 上午 (9-12点)": list(range(9, 12)),
    "🍚 午间 (12-14点)": list(range(12, 14)),
    "🌤️ 下午 (14-18点)": list(range(14, 18)),
    "🌆 傍晚 (18-21点)": list(range(18, 21)),
    "🌃 晚上 (21-24点)": list(range(21, 24))
}

# Calculate block distributions based on process start times
block_counts = {block: 0 for block in blocks}
app_in_blocks = {block: defaultdict(int) for block in blocks}

for proc in []:  # Would need historical data
    pass

# For now, show current distribution mapped to blocks
current_hour = datetime.now().hour
for block_name, hours in blocks.items():
    if current_hour in hours:
        apps = hourly_data.get(current_hour, [])
        if apps:
            app_counts = Counter(apps)
            total = len(apps)
            print(f"{block_name} (当前时段)")
            for app, cnt in app_counts.most_common(3):
                pct = cnt / total * 100
                bar = "█" * int(pct / 5)
                print(f"   {app:<20} {bar} {pct:.0f}%")
            break

print("-" * 70)
print("\n💡 提示: 开启定时采集后，可生成完整的历史时段分析报告")
print("=" * 70)
