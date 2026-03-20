# -*- coding: utf-8 -*-
"""
可视化图表模块
使用 matplotlib 生成分类饼图、活跃度柱状图、趋势折线图
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter

sys.path.insert(0, str(Path(__file__).parent.parent))
from app_categories import classify_app

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
CHART_DIR = DATA_DIR / "reports" / "charts"

# 分类颜色映射
CATEGORY_COLORS = {
    "开发": "#9b59b6",
    "工作": "#3498db",
    "社交": "#f1c40f",
    "娱乐": "#e74c3c",
    "系统": "#95a5a6",
    "其他": "#bdc3c7"
}


def setup_chinese_font():
    """配置 matplotlib 中文字体"""
    import matplotlib
    import matplotlib.font_manager as fm

    font_names = ['SimHei', 'Microsoft YaHei', 'STHeiti', 'WenQuanYi Micro Hei']
    for font_name in font_names:
        fonts = [f for f in fm.fontManager.ttflist if font_name in f.name]
        if fonts:
            matplotlib.rcParams['font.sans-serif'] = [font_name]
            matplotlib.rcParams['axes.unicode_minus'] = False
            return
    # fallback
    matplotlib.rcParams['font.sans-serif'] = ['sans-serif']
    matplotlib.rcParams['axes.unicode_minus'] = False
    print("⚠️ 未找到中文字体，图表中文可能显示异常")


def load_data(date):
    """加载指定日期的数据"""
    data_file = DATA_DIR / f"usage_{date}.json"
    if data_file.exists():
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def generate_category_pie(records, output_path=None):
    """生成分类使用时长饼图"""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("❌ 需要安装 matplotlib: pip install matplotlib")
        return None

    if not records or len(records) < 2:
        print("⚠️ 数据不足，无法生成饼图")
        return None

    setup_chinese_font()

    category_duration = defaultdict(float)
    for r in records:
        cat, _ = classify_app(r.get('Name', 'Unknown'))
        category_duration[cat] += r.get('DurationMinutes', 0)

    # 过滤掉时长为0的分类
    categories = {k: v for k, v in category_duration.items() if v > 0}
    if len(categories) < 2:
        print("⚠️ 分类数不足，无法生成饼图")
        return None

    labels = list(categories.keys())
    sizes = list(categories.values())
    colors = [CATEGORY_COLORS.get(l, '#bdc3c7') for l in labels]

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax.set_title('应用分类使用时长分布')

    if output_path is None:
        CHART_DIR.mkdir(parents=True, exist_ok=True)
        output_path = CHART_DIR / f"category_pie_{datetime.now().strftime('%Y-%m-%d')}.png"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ 饼图已保存: {output_path}")
    return output_path


def generate_hourly_bar(records, output_path=None):
    """生成每小时活跃度柱状图"""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("❌ 需要安装 matplotlib: pip install matplotlib")
        return None

    if not records:
        print("⚠️ 数据不足，无法生成柱状图")
        return None

    setup_chinese_font()

    hourly = Counter()
    for r in records:
        hourly[r.get('hour', 0)] += 1

    hours = list(range(24))
    counts = [hourly.get(h, 0) for h in hours]

    fig, ax = plt.subplots(figsize=(12, 5))
    bars = ax.bar(hours, counts, color='#3498db', alpha=0.8)

    # 高亮高峰时段
    max_count = max(counts) if counts else 0
    for bar, count in zip(bars, counts):
        if count > max_count * 0.7:
            bar.set_color('#e74c3c')

    ax.set_xlabel('小时')
    ax.set_ylabel('活跃记录数')
    ax.set_title('每小时活跃度分布')
    ax.set_xticks(hours)

    if output_path is None:
        CHART_DIR.mkdir(parents=True, exist_ok=True)
        output_path = CHART_DIR / f"hourly_bar_{datetime.now().strftime('%Y-%m-%d')}.png"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ 柱状图已保存: {output_path}")
    return output_path


def generate_weekly_trend(dates=None, output_path=None):
    """生成周趋势折线图（每日总使用时长变化）"""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("❌ 需要安装 matplotlib: pip install matplotlib")
        return None

    setup_chinese_font()

    if dates is None:
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        dates = [(week_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    daily_duration = []
    valid_dates = []
    for date in dates:
        data = load_data(date)
        if data and data.get('records'):
            total = sum(r.get('DurationMinutes', 0) for r in data['records'])
            daily_duration.append(total / 60)  # 转为小时
            valid_dates.append(date[-5:])  # MM-DD
        else:
            daily_duration.append(0)
            valid_dates.append(date[-5:])

    if not any(d > 0 for d in daily_duration):
        print("⚠️ 数据不足，无法生成趋势图")
        return None

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(valid_dates, daily_duration, 'o-', color='#3498db', linewidth=2, markersize=8)
    ax.fill_between(range(len(valid_dates)), daily_duration, alpha=0.1, color='#3498db')
    ax.set_xlabel('日期')
    ax.set_ylabel('使用时长 (小时)')
    ax.set_title('周使用时长趋势')
    ax.grid(True, alpha=0.3)

    if output_path is None:
        CHART_DIR.mkdir(parents=True, exist_ok=True)
        output_path = CHART_DIR / f"weekly_trend_{datetime.now().strftime('%Y-%m-%d')}.png"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ 趋势图已保存: {output_path}")
    return output_path


def generate_all_charts(date_str=None):
    """生成所有图表"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    data = load_data(date_str)
    if not data or not data.get('records'):
        print(f"❌ {date_str} 无数据，无法生成图表")
        return

    records = data['records']
    print(f"📊 为 {date_str} 生成图表...")
    generate_category_pie(records)
    generate_hourly_bar(records)
    generate_weekly_trend()
    print("✅ 所有图表生成完成")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='生成可视化图表')
    parser.add_argument('--date', type=str, help='指定日期 (YYYY-MM-DD)')
    parser.add_argument('--pie', action='store_true', help='仅生成饼图')
    parser.add_argument('--bar', action='store_true', help='仅生成柱状图')
    parser.add_argument('--trend', action='store_true', help='仅生成趋势图')
    args = parser.parse_args()

    date = args.date or datetime.now().strftime("%Y-%m-%d")
    data = load_data(date)
    records = data.get('records', []) if data else []

    if args.pie:
        generate_category_pie(records)
    elif args.bar:
        generate_hourly_bar(records)
    elif args.trend:
        generate_weekly_trend()
    else:
        generate_all_charts(date)
