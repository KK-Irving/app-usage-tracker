# -*- coding: utf-8 -*-
"""
JSON → SQLite 数据迁移工具
将 V1 格式的 JSON 数据文件批量导入到 SQLite 数据库
支持 --dry-run 模式预览迁移数据量
"""
import argparse
import json
import sys
from pathlib import Path

# 确保能导入根目录模块
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.data_store import DataStore, DATA_DIR


def find_usage_files():
    """查找所有 usage_*.json 数据文件"""
    return sorted(DATA_DIR.glob("usage_*.json"))


def load_usage_json(filepath):
    """
    加载单个 usage JSON 文件
    V1 格式: {"date": "YYYY-MM-DD", "records": [...]}
    Returns:
        (date, records) 元组，失败时返回 (None, [])
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        date = data.get("date", "")
        records = data.get("records", [])
        return date, records
    except (json.JSONDecodeError, IOError) as e:
        print(f"  ⚠️ 读取失败: {filepath} ({e})")
        return None, []


def load_focus_sessions():
    """
    加载 focus_sessions.json
    V1 格式: {"sessions": [...], "daily_stats": {...}}
    Returns:
        专注会话列表
    """
    filepath = DATA_DIR / "focus_sessions.json"
    if not filepath.exists():
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 兼容两种格式：dict 或 list
        if isinstance(data, dict) and "sessions" in data:
            return data["sessions"]
        elif isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, IOError) as e:
        print(f"  ⚠️ 读取 focus_sessions.json 失败: {e}")
        return []


def migrate(dry_run=False):
    """
    执行 JSON → SQLite 迁移
    Args:
        dry_run: 仅预览迁移数据量，不实际写入
    """
    print("=" * 60)
    if dry_run:
        print("🔍 数据迁移预览 (dry-run 模式)")
    else:
        print("🚀 开始 JSON → SQLite 数据迁移")
    print("=" * 60)

    # --- 迁移 usage 记录 ---
    usage_files = find_usage_files()
    total_usage_records = 0
    total_usage_files = len(usage_files)
    migrated_files = 0
    failed_files = 0

    print(f"\n📂 发现 {total_usage_files} 个 usage 数据文件")

    if not dry_run:
        store = DataStore(backend="sqlite")

    for i, filepath in enumerate(usage_files, 1):
        date, records = load_usage_json(filepath)
        if date is None:
            failed_files += 1
            continue

        record_count = len(records)
        total_usage_records += record_count
        migrated_files += 1

        # 显示进度
        print(f"  [{i}/{total_usage_files}] {filepath.name}: {record_count} 条记录 (日期: {date})")

        if not dry_run and records:
            store.save_usage_records(records, date)

    # --- 迁移 focus_sessions ---
    focus_sessions = load_focus_sessions()
    total_focus = len(focus_sessions)

    print(f"\n📂 发现 {total_focus} 条专注会话记录")

    if not dry_run and focus_sessions:
        for j, session in enumerate(focus_sessions, 1):
            # 标准化字段名
            normalized = {
                "date": session.get("date", ""),
                "duration_minutes": session.get("duration_minutes", session.get("duration", 0)),
                "timestamp": session.get("timestamp", ""),
                "app_name": session.get("app_name", session.get("app", "")),
                "category": session.get("category", ""),
            }
            store.save_focus_session(normalized)

        print(f"  ✅ 已迁移 {total_focus} 条专注会话")

    # --- 输出统计 ---
    print("\n" + "=" * 60)
    print("📊 迁移统计:")
    print(f"  Usage 文件数:    {migrated_files}/{total_usage_files}")
    if failed_files > 0:
        print(f"  失败文件数:      {failed_files}")
    print(f"  Usage 记录总数:  {total_usage_records}")
    print(f"  专注会话总数:    {total_focus}")
    print(f"  迁移记录合计:    {total_usage_records + total_focus}")

    if dry_run:
        print("\n💡 这是 dry-run 预览，未实际写入数据库")
        print("   移除 --dry-run 参数执行实际迁移")
    else:
        store.close()
        print(f"\n✅ 迁移完成! 数据已写入 {DATA_DIR / 'usage_tracker.db'}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="JSON → SQLite 数据迁移工具")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅预览迁移数据量，不实际写入数据库"
    )
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
