# -*- coding: utf-8 -*-
"""
定时任务调度器
通过 Windows 任务计划程序设置自动采集
"""
import sys
import io
import subprocess
import json
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).parent.parent
COLLECT_SCRIPT = ROOT_DIR / "scripts" / "collect_usage.py"
MAIN_SCRIPT = ROOT_DIR / "app_usage_tracker.py"
CONFIG_FILE = ROOT_DIR / "config.json"


def load_config():
    """加载配置"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"interval_minutes": 60}


def run_collection():
    """执行一次数据采集"""
    print(f"🕐 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始采集...")
    try:
        result = subprocess.run(
            [sys.executable, str(COLLECT_SCRIPT)],
            capture_output=True, text=True, encoding='utf-8', timeout=60
        )
        if result.returncode == 0:
            print(result.stdout)
            print("✅ 采集完成")
        else:
            print(f"❌ 采集失败: {result.stderr}")
    except Exception as e:
        print(f"❌ 错误: {e}")


def setup_windows_task():
    """通过 Windows 任务计划程序设置定时采集"""
    config = load_config()
    interval = config.get('interval_minutes', 60)
    python_path = sys.executable
    script_path = str(COLLECT_SCRIPT.resolve())
    task_name = "AppUsageTracker_Collect"

    # 删除已有任务（忽略错误）
    subprocess.run(
        ["schtasks", "/Delete", "/TN", task_name, "/F"],
        capture_output=True, text=True
    )

    # 创建新的计划任务
    cmd = [
        "schtasks", "/Create",
        "/TN", task_name,
        "/TR", f'"{python_path}" "{script_path}"',
        "/SC", "MINUTE",
        "/MO", str(interval),
        "/F"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

    if result.returncode == 0:
        print(f"✅ 已创建 Windows 计划任务: {task_name}")
        print(f"   执行间隔: 每 {interval} 分钟")
        print(f"   Python: {python_path}")
        print(f"   脚本: {script_path}")
    else:
        print(f"❌ 创建计划任务失败: {result.stderr}")
        print("💡 提示: 可能需要以管理员权限运行")


def remove_windows_task():
    """移除 Windows 计划任务"""
    task_names = [
        "AppUsageTracker_Collect",
        "AppUsageTracker_DailyReport",
        "AppUsageTracker_DailyExport"
    ]
    for task_name in task_names:
        result = subprocess.run(
            ["schtasks", "/Delete", "/TN", task_name, "/F"],
            capture_output=True, text=True, encoding='utf-8'
        )
        if result.returncode == 0:
            print(f"✅ 已移除计划任务: {task_name}")
        else:
            print(f"⚠️ 移除失败或任务不存在: {task_name}")


def setup_daily_report_task(run_time="23:00"):
    """设置每日自动生成报告的计划任务"""
    python_path = sys.executable
    script_path = str(MAIN_SCRIPT.resolve())
    task_name = "AppUsageTracker_DailyReport"

    subprocess.run(
        ["schtasks", "/Delete", "/TN", task_name, "/F"],
        capture_output=True, text=True
    )

    cmd = [
        "schtasks", "/Create",
        "/TN", task_name,
        "/TR", f'"{python_path}" "{script_path}" daily',
        "/SC", "DAILY",
        "/ST", run_time,
        "/F"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    if result.returncode == 0:
        print(f"✅ 已创建每日报告任务: {task_name}")
        print(f"   执行时间: 每天 {run_time}")
    else:
        print(f"❌ 创建失败: {result.stderr}")
        print("💡 提示: 可能需要以管理员权限运行")


def setup_daily_export_task(run_time="23:30"):
    """设置每日自动导出 CSV 的计划任务"""
    python_path = sys.executable
    script_path = str(MAIN_SCRIPT.resolve())
    task_name = "AppUsageTracker_DailyExport"

    subprocess.run(
        ["schtasks", "/Delete", "/TN", task_name, "/F"],
        capture_output=True, text=True
    )

    cmd = [
        "schtasks", "/Create",
        "/TN", task_name,
        "/TR", f'"{python_path}" "{script_path}" export --daily',
        "/SC", "DAILY",
        "/ST", run_time,
        "/F"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    if result.returncode == 0:
        print(f"✅ 已创建每日导出任务: {task_name}")
        print(f"   执行时间: 每天 {run_time}")
    else:
        print(f"❌ 创建失败: {result.stderr}")
        print("💡 提示: 可能需要以管理员权限运行")


def setup_all_tasks():
    """一键设置所有定时任务"""
    print("📋 设置所有定时任务...\n")
    setup_windows_task()
    print()
    setup_daily_report_task()
    print()
    setup_daily_export_task()
    print("\n✅ 所有定时任务设置完成")


def list_tasks():
    """列出当前已注册的计划任务"""
    task_names = [
        ("AppUsageTracker_Collect", "定时采集"),
        ("AppUsageTracker_DailyReport", "每日报告"),
        ("AppUsageTracker_DailyExport", "每日导出"),
    ]
    print("📋 App Usage Tracker 计划任务状态:\n")
    for task_name, desc in task_names:
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", task_name, "/FO", "LIST"],
            capture_output=True, text=True, encoding='utf-8'
        )
        if result.returncode == 0:
            # 提取下次运行时间
            for line in result.stdout.splitlines():
                if "下次运行时间" in line or "Next Run Time" in line:
                    print(f"  ✅ {desc} ({task_name}): {line.split(':',1)[-1].strip()}")
                    break
            else:
                print(f"  ✅ {desc} ({task_name}): 已注册")
        else:
            print(f"  ❌ {desc} ({task_name}): 未注册")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='应用使用数据采集调度器')
    parser.add_argument('--run', '-r', action='store_true', help='立即执行一次采集')
    parser.add_argument('--setup', '-s', action='store_true', help='设置定时采集任务')
    parser.add_argument('--setup-report', action='store_true', help='设置每日报告任务')
    parser.add_argument('--setup-export', action='store_true', help='设置每日导出任务')
    parser.add_argument('--setup-all', action='store_true', help='一键设置所有定时任务')
    parser.add_argument('--remove', action='store_true', help='移除所有定时任务')
    parser.add_argument('--list', '-l', action='store_true', help='列出计划任务状态')
    parser.add_argument('--time', type=str, default=None, help='指定执行时间 (HH:MM)')
    args = parser.parse_args()

    if args.setup_all:
        setup_all_tasks()
    elif args.setup:
        setup_windows_task()
    elif args.setup_report:
        setup_daily_report_task(args.time or "23:00")
    elif args.setup_export:
        setup_daily_export_task(args.time or "23:30")
    elif args.remove:
        remove_windows_task()
    elif args.list:
        list_tasks()
    elif args.run:
        run_collection()
    else:
        list_tasks()


if __name__ == "__main__":
    main()
