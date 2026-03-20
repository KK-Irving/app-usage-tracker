# -*- coding: utf-8 -*-
"""
超时提醒功能
当某个应用使用时间过长时发送通知
"""
import time
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import psutil

# 配置文件路径
ROOT_DIR = Path(__file__).parent.parent
CONFIG_DIR = ROOT_DIR / "config"
TIMEOUT_CONFIG = CONFIG_DIR / "timeout_alerts.json"

# 默认超时配置 (分钟)
DEFAULT_ALERTS = {
    "chrome": 120,      # Chrome 超过2小时提醒
    "微信": 60,         # 微信超过1小时提醒
    "WeChat": 60,
    "DingTalk": 120,    # 钉钉超过2小时提醒
    "钉钉": 120,
    "QQ": 60,
    "抖音": 30,         # 抖音超过30分钟提醒
    "douyin": 30,
    "bilibili": 60,    # B站超过1小时提醒
    "小红书": 30,
    "xiaohongshu": 30
}

def load_alert_config():
    """加载超时配置"""
    if TIMEOUT_CONFIG.exists():
        import json
        with open(TIMEOUT_CONFIG, 'r', encoding='utf-8') as f:
            return json.load(f)
    return DEFAULT_ALERTS

def save_alert_config(config):
    """保存超时配置"""
    import json
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(TIMEOUT_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def check_app_timeouts(alert_config=None):
    """检查应用是否超时"""
    if alert_config is None:
        alert_config = load_alert_config()
    
    current_time = time.time()
    alerts = []
    
    # 按应用分组统计运行时长
    app_sessions = defaultdict(lambda: {'duration': 0, 'count': 0, 'pids': []})
    
    for p in psutil.process_iter(['name', 'create_time', 'pid']):
        try:
            info = p.info
            name = info['name']
            if not name:
                continue
            
            create_time = info.get('create_time')
            if not create_time:
                continue
            
            duration_min = (current_time - create_time) / 60
            
            # 检查是否在告警列表中
            for alert_app, threshold in alert_config.items():
                if alert_app.lower() in name.lower():
                    if duration_min >= threshold:
                        alerts.append({
                            'app': name,
                            'duration': duration_min,
                            'threshold': threshold,
                            'pids': [info['pid']]
                        })
                    break
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    return alerts

def send_notification(title, message):
    """发送系统通知"""
    try:
        # 使用 PowerShell 发送 Windows 通知
        ps_script = f'''
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
        
        $template = @"
        <toast>
            <visual>
                <binding template="ToastText02">
                    <text id="1">{title}</text>
                    <text id="2">{message}</text>
                </binding>
            </visual>
        </toast>
"@
        
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("App Usage Tracker").Show($toast)
        '''
        
        import subprocess
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            timeout=10
        )
        return True
    except Exception as e:
        print(f"发送通知失败: {e}")
        return False

def monitor_loop(interval=300, alert_config=None):
    """监控循环"""
    import argparse
    
    parser = argparse.ArgumentParser(description='应用超时监控')
    parser.add_argument('--interval', '-i', type=int, default=300, help='检查间隔(秒), 默认300秒')
    parser.add_argument('--once', '-o', action='store_true', help='只检查一次')
    args = parser.parse_args()
    
    if alert_config is None:
        alert_config = load_alert_config()
    
    print(f"🔔 应用超时监控已启动 (检查间隔: {args.interval}秒)")
    print(f"告警配置: {alert_config}")
    print("-" * 50)
    
    notified_today = set()
    
    while True:
        now = datetime.now().strftime("%Y-%m-%d")
        
        # 每天重置通知记录
        if now not in [k.split('_')[0] for k in notified_today] or not notified_today:
            notified_today.clear()
        
        alerts = check_app_timeouts(alert_config)
        
        for alert in alerts:
            key = f"{now}_{alert['app']}"
            
            if key not in notified_today:
                hrs = int(alert['duration'] // 60)
                mins = int(alert['duration'] % 60)
                
                title = "⏰ 应用超时提醒"
                message = f"{alert['app']} 已使用 {hrs}h {mins}m (超过{alert['threshold']}分钟)"
                
                print(f"🔔 {message}")
                send_notification(title, message)
                
                notified_today.add(key)
        
        if args.once:
            break
        
        time.sleep(args.interval)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='应用超时提醒')
    parser.add_argument('--check', '-c', action='store_true', help='检查当前超时的应用')
    parser.add_argument('--list', '-l', action='store_true', help='列出告警配置')
    parser.add_argument('--add', '-a', nargs=2, type=str, help='添加告警: 应用名 阈值(分钟)')
    parser.add_argument('--remove', '-r', type=str, help='移除告警: 应用名')
    parser.add_argument('--monitor', '-m', action='store_true', help='启动监控模式')
    parser.add_argument('--interval', '-i', type=int, default=300, help='监控间隔(秒)')
    args = parser.parse_args()
    
    config = load_alert_config()
    
    if args.list:
        print("📋 当前告警配置:")
        for app, threshold in sorted(config.items(), key=lambda x: x[1]):
            print(f"  {app}: {threshold}分钟")
    
    elif args.add:
        app_name, threshold = args.add
        config[app_name] = int(threshold)
        save_alert_config(config)
        print(f"✅ 已添加: {app_name} = {threshold}分钟")
    
    elif args.remove:
        if args.remove in config:
            del config[args.remove]
            save_alert_config(config)
            print(f"✅ 已移除: {args.remove}")
        else:
            print(f"❌ 未找到: {args.remove}")
    
    elif args.check:
        print("🔍 检查超时应用...")
        alerts = check_app_timeouts(config)
        if alerts:
            for alert in alerts:
                hrs = int(alert['duration'] // 60)
                mins = int(alert['duration'] % 60)
                print(f"  ⚠️ {alert['app']}: {hrs}h {mins}m (阈值: {alert['threshold']}分钟)")
        else:
            print("  ✅ 没有应用超时")
    
    elif args.monitor:
        monitor_loop(args.interval, config)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
