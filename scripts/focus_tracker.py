# -*- coding: utf-8 -*-
"""
专注力追踪器
类似番茄钟，记录深度工作时长，生成专注力报告
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))
from app_categories import classify_app

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
FOCUS_FILE = DATA_DIR / "focus_sessions.json"
CONFIG_FILE = ROOT_DIR / "config.json"


def load_config():
    """加载配置"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"focus_threshold_minutes": 25}


def load_focus_data():
    """加载专注数据（优先使用 DataStore）"""
    try:
        from scripts.data_store import DataStore
        store = DataStore()
        sessions = store.get_focus_sessions()
        store.close()
        return {"sessions": sessions, "daily_stats": {}}
    except Exception:
        pass
    if FOCUS_FILE.exists():
        with open(FOCUS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"sessions": [], "daily_stats": {}}


def save_focus_data(data):
    """保存专注数据（同时写入 DataStore 和 JSON）"""
    # V2: 写入 DataStore
    try:
        from scripts.data_store import DataStore
        store = DataStore()
        for session in data.get("sessions", []):
            if not session.get("_saved"):
                store.save_focus_session({
                    "date": session.get("date", ""),
                    "duration_minutes": session.get("duration_minutes", session.get("duration", 0)),
                    "timestamp": session.get("timestamp", ""),
                    "app_name": session.get("app_name", session.get("app", "")),
                    "category": session.get("category", ""),
                })
        store.close()
    except Exception:
        pass
    # V1 兼容: 也写入 JSON
    FOCUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FOCUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def detect_focus_sessions(records, threshold_min=25):
    """
    检测专注时段
    基于连续使用工作/开发类应用的时长
    """
    sorted_records = sorted(records, key=lambda x: x.get('timestamp', ''))
    sessions = []
    current_session = None

    for record in sorted_records:
        app = record.get('Name', 'Unknown')
        duration = record.get('DurationMinutes', 0)
        category, _ = classify_app(app)

        if category not in ['工作', '开发']:
            if current_session and current_session['duration'] >= threshold_min:
                sessions.append(current_session)
            current_session = None
            continue

        if current_session is None or current_session['app'] != app:
            if current_session and current_session['duration'] >= threshold_min:
                sessions.append(current_session)
            current_session = {'app': app, 'duration': duration, 'category': category}
        else:
            current_session['duration'] += duration

    if current_session and current_session['duration'] >= threshold_min:
        sessions.append(current_session)

    return sessions


def calculate_focus_score(records):
    """
    计算专注度分数
    Returns:
        (分数 0-100, 状态标签)
    """
    if not records:
        return 0, "无数据"

    category_minutes = defaultdict(float)
    for record in records:
        app = record.get('Name', 'Unknown')
        category, _ = classify_app(app)
        category_minutes[category] += record.get('DurationMinutes', 0)

    total = sum(category_minutes.values())
    if total == 0:
        return 0, "无数据"

    focus_minutes = category_minutes.get('工作', 0) + category_minutes.get('开发', 0)
    score = (focus_minutes / total) * 100

    if score >= 80:
        return score, "🔥 高度专注"
    elif score >= 60:
        return score, "⚡ 较为专注"
    elif score >= 40:
        return score, "⚠️ 注意力分散"
    else:
        return score, "😴 休闲模式"


def analyze_daily_focus(date_str=None):
    """分析指定日期的专注力"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    data_file = DATA_DIR / f"usage_{date_str}.json"
    if not data_file.exists():
        print(f"❌ {date_str} 暂无数据，请先运行采集")
        return None

    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = data.get('records', [])
    config = load_config()
    threshold = config.get('focus_threshold_minutes', 25)

    score, status = calculate_focus_score(records)
    sessions = detect_focus_sessions(records, threshold)

    print("=" * 60)
    print("🎯 专注力分析")
    print("=" * 60)
    print(f"  专注度分数: {score:.0f}/100 - {status}")
    print(f"  检测到专注时段: {len(sessions)} 个")

    if sessions:
        print("\n  专注时段:")
        for i, s in enumerate(sessions[:5], 1):
            hrs = int(s['duration'] // 60)
            mins = int(s['duration'] % 60)
            print(f"    {i}. {s['app']:<20} {hrs}h {mins}m [{s['category']}]")

    # 按分类统计
    print("\n  分类使用:")
    category_minutes = defaultdict(float)
    for record in records:
        app = record.get('Name', 'Unknown')
        category, icon = classify_app(app)
        category_minutes[category] += record.get('DurationMinutes', 0)

    total = sum(category_minutes.values())
    for cat, mins in sorted(category_minutes.items(), key=lambda x: x[1], reverse=True):
        if mins > 0:
            pct = mins / total * 100 if total > 0 else 0
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            hrs = int(mins // 60)
            m = int(mins % 60)
            _, icon = classify_app(cat)  # 获取图标
            print(f"    {cat:<6} {bar} {hrs}h {m}m ({pct:.0f}%)")

    print("=" * 60)

    # V2: 切换频率-专注度相关性
    try:
        from scripts.data_store import DataStore
        from scripts.switch_analyzer import SwitchAnalyzer
        store = DataStore()
        sa = SwitchAnalyzer(store)
        corr_data = sa.get_switch_focus_correlation(date_str)
        store.close()
        if corr_data.get("hourly_data"):
            print(f"\n🔄 切换频率-专注度相关性: {corr_data['correlation']:.2f}")
            if corr_data['correlation'] < -0.3:
                print("  → 切换越频繁，专注度越低（负相关）")
            elif corr_data['correlation'] > 0.3:
                print("  → 切换与专注度正相关（可能是多任务高效模式）")
            else:
                print("  → 切换频率与专注度无明显相关性")
    except Exception:
        pass

    return score, sessions


def start_focus_timer(duration_minutes=25):
    """开始一个专注计时器（番茄钟模式）"""
    print(f"🍅 开始专注计时: {duration_minutes} 分钟")
    print("=" * 60)

    start_time = time.time()
    end_time = start_time + duration_minutes * 60

    try:
        while time.time() < end_time:
            remaining = int((end_time - time.time()) / 60)
            print(f"\r  剩余: {remaining} 分钟", end="", flush=True)
            time.sleep(60)

        print("\n\n✅ 专注时间结束!")

        data = load_focus_data()
        data['sessions'].append({
            'date': datetime.now().strftime("%Y-%m-%d"),
            'duration': duration_minutes,
            'timestamp': datetime.now().isoformat()
        })
        save_focus_data(data)
        print(f"  已记录 {duration_minutes} 分钟专注时长")

    except KeyboardInterrupt:
        elapsed = int((time.time() - start_time) / 60)
        print(f"\n\n⚠️ 专注计时已取消 (已专注 {elapsed} 分钟)")
        if elapsed >= 5:
            data = load_focus_data()
            data['sessions'].append({
                'date': datetime.now().strftime("%Y-%m-%d"),
                'duration': elapsed,
                'timestamp': datetime.now().isoformat()
            })
            save_focus_data(data)
            print(f"  已记录 {elapsed} 分钟专注时长")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='专注力追踪')
    parser.add_argument('--analyze', action='store_true', help='分析专注力')
    parser.add_argument('--date', type=str, help='指定日期 (YYYY-MM-DD)')
    parser.add_argument('--timer', type=int, default=None, help='开始专注计时(分钟)')
    args = parser.parse_args()

    if args.timer is not None:
        start_focus_timer(args.timer)
    else:
        analyze_daily_focus(args.date)
