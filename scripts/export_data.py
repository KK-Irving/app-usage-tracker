# -*- coding: utf-8 -*-
"""
数据导出脚本
支持导出 CSV 格式，便于 Excel 分析
"""
import json
import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"


def load_data(date):
    """加载指定日期的数据"""
    data_file = DATA_DIR / f"usage_{date}.json"
    if data_file.exists():
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


FIELDNAMES = ['timestamp', 'hour', 'Name', 'Category', 'CPU', 'MemoryMB', 'DurationMinutes']


def _write_csv(records, csv_file):
    """写入 CSV 文件（utf-8-sig 编码）"""
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for record in records:
            row = {k: record.get(k, '') for k in FIELDNAMES}
            writer.writerow(row)
    return csv_file


def export_daily_csv(date):
    """导出单日数据为 CSV"""
    data = load_data(date)
    if not data or not data.get('records'):
        print(f"❌ {date} 无数据")
        return None

    csv_file = DATA_DIR / f"export_{date}.csv"
    _write_csv(data['records'], csv_file)
    print(f"✅ 已导出: {csv_file} ({len(data['records'])} 条记录)")
    return csv_file


def export_weekly_csv():
    """导出本周数据为 CSV"""
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    dates = [(week_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    all_records = []
    for date in dates:
        data = load_data(date)
        if data and data.get('records'):
            all_records.extend(data['records'])

    if not all_records:
        print("❌ 本周无数据")
        return None

    csv_file = DATA_DIR / f"export_weekly_{today.strftime('%Y-%m-%d')}.csv"
    _write_csv(all_records, csv_file)
    print(f"✅ 已导出: {csv_file} ({len(all_records)} 条记录)")
    return csv_file


def export_monthly_csv():
    """导出本月数据为 CSV"""
    today = datetime.now()
    month_start = datetime(today.year, today.month, 1)
    dates = []
    current = month_start
    while current <= today:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    all_records = []
    for date in dates:
        data = load_data(date)
        if data and data.get('records'):
            all_records.extend(data['records'])

    if not all_records:
        print("❌ 本月无数据")
        return None

    csv_file = DATA_DIR / f"export_monthly_{today.strftime('%Y-%m-%d')}.csv"
    _write_csv(all_records, csv_file)
    print(f"✅ 已导出: {csv_file} ({len(all_records)} 条记录)")
    return csv_file


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='导出应用使用数据为CSV')
    parser.add_argument('--daily', type=str, help='导出单日数据 (YYYY-MM-DD)')
    parser.add_argument('--weekly', action='store_true', help='导出本周数据')
    parser.add_argument('--monthly', action='store_true', help='导出本月数据')
    args = parser.parse_args()

    if args.daily:
        export_daily_csv(args.daily)
    elif args.weekly:
        export_weekly_csv()
    elif args.monthly:
        export_monthly_csv()
    else:
        today = datetime.now().strftime("%Y-%m-%d")
        export_daily_csv(today)
