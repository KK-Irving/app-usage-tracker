# -*- coding: utf-8 -*-
"""
统一数据访问层 (DataStore)
支持 SQLite 和 JSON 双后端，所有模块通过此接口读写数据
"""
import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path

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
    return {"storage_backend": "sqlite"}


class SQLiteBackend:
    """SQLite 存储后端"""

    def __init__(self, db_path=None):
        """
        Args:
            db_path: 数据库文件路径，默认为 data/usage_tracker.db
        """
        if db_path is None:
            db_path = DATA_DIR / "usage_tracker.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        """初始化所有表结构和索引"""
        cursor = self.conn.cursor()

        # 使用记录表（V1 数据 + V2 新增字段）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                hour INTEGER NOT NULL,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                cpu REAL DEFAULT 0,
                memory_mb REAL DEFAULT 0,
                duration_minutes REAL DEFAULT 0,
                is_foreground INTEGER DEFAULT 0,
                foreground_minutes REAL DEFAULT 0,
                device_id TEXT DEFAULT 'local'
            )
        """)

        # 前台会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS foreground_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                window_title TEXT DEFAULT '',
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                duration_seconds REAL NOT NULL
            )
        """)

        # 专注会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS focus_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                duration_minutes REAL NOT NULL,
                timestamp TEXT NOT NULL,
                app_name TEXT DEFAULT '',
                category TEXT DEFAULT ''
            )
        """)

        # 上下文切换表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_switches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                from_app TEXT NOT NULL,
                to_app TEXT NOT NULL
            )
        """)

        # 项目会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                app_name TEXT NOT NULL,
                workspace_path TEXT DEFAULT '',
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                duration_minutes REAL NOT NULL
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_records(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_date ON usage_records(substr(timestamp, 1, 10))")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_device ON usage_records(device_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fg_start ON foreground_sessions(start_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_focus_date ON focus_sessions(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_switch_timestamp ON context_switches(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_proj_name ON project_sessions(project_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_proj_start ON project_sessions(start_time)")

        self.conn.commit()

    # --- Usage Records ---

    def save_usage_records(self, records, date):
        """保存使用记录（追加模式）"""
        cursor = self.conn.cursor()
        for r in records:
            cursor.execute("""
                INSERT INTO usage_records
                (timestamp, hour, name, category, cpu, memory_mb,
                 duration_minutes, is_foreground, foreground_minutes, device_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r.get("timestamp", ""),
                r.get("hour", 0),
                r.get("name", r.get("Name", "")),
                r.get("category", r.get("Category", "其他")),
                r.get("cpu", r.get("CPU", 0)),
                r.get("memory_mb", r.get("MemoryMB", 0)),
                r.get("duration_minutes", r.get("DurationMinutes", 0)),
                r.get("is_foreground", 0),
                r.get("foreground_minutes", 0),
                r.get("device_id", "local"),
            ))
        self.conn.commit()

    def get_usage_records(self, date):
        """获取指定日期的使用记录"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM usage_records WHERE substr(timestamp, 1, 10) = ?",
            (date,)
        )
        return [self._row_to_usage_dict(row) for row in cursor.fetchall()]

    def get_usage_records_range(self, start_date, end_date):
        """获取日期范围内的使用记录"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM usage_records WHERE substr(timestamp, 1, 10) >= ? AND substr(timestamp, 1, 10) <= ?",
            (start_date, end_date)
        )
        return [self._row_to_usage_dict(row) for row in cursor.fetchall()]

    def _row_to_usage_dict(self, row):
        """将 SQLite Row 转换为字典"""
        return {
            "timestamp": row["timestamp"],
            "hour": row["hour"],
            "name": row["name"],
            "Name": row["name"],
            "category": row["category"],
            "Category": row["category"],
            "cpu": row["cpu"],
            "CPU": row["cpu"],
            "memory_mb": row["memory_mb"],
            "MemoryMB": row["memory_mb"],
            "duration_minutes": row["duration_minutes"],
            "DurationMinutes": row["duration_minutes"],
            "is_foreground": row["is_foreground"],
            "foreground_minutes": row["foreground_minutes"],
            "device_id": row["device_id"],
        }

    # --- Foreground Sessions ---

    def save_foreground_session(self, session):
        """保存一条前台会话"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO foreground_sessions
            (app_name, window_title, start_time, end_time, duration_seconds)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session.get("app_name", ""),
            session.get("window_title", ""),
            session.get("start_time", ""),
            session.get("end_time", ""),
            session.get("duration_seconds", 0),
        ))
        self.conn.commit()

    def get_foreground_sessions(self, date):
        """获取指定日期的前台会话"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM foreground_sessions WHERE substr(start_time, 1, 10) = ?",
            (date,)
        )
        return [self._row_to_fg_dict(row) for row in cursor.fetchall()]

    def _row_to_fg_dict(self, row):
        """将前台会话 Row 转换为字典"""
        return {
            "app_name": row["app_name"],
            "window_title": row["window_title"],
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "duration_seconds": row["duration_seconds"],
        }

    # --- Context Switches ---

    def save_context_switch(self, switch):
        """保存一条切换事件"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO context_switches (timestamp, from_app, to_app)
            VALUES (?, ?, ?)
        """, (
            switch.get("timestamp", ""),
            switch.get("from_app", ""),
            switch.get("to_app", ""),
        ))
        self.conn.commit()

    def get_context_switches(self, date):
        """获取指定日期的切换事件"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM context_switches WHERE substr(timestamp, 1, 10) = ?",
            (date,)
        )
        return [self._row_to_switch_dict(row) for row in cursor.fetchall()]

    def _row_to_switch_dict(self, row):
        """将切换事件 Row 转换为字典"""
        return {
            "timestamp": row["timestamp"],
            "from_app": row["from_app"],
            "to_app": row["to_app"],
        }

    # --- Project Sessions ---

    def save_project_session(self, session):
        """保存一条项目会话"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO project_sessions
            (project_name, app_name, workspace_path, start_time, end_time, duration_minutes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session.get("project_name", ""),
            session.get("app_name", ""),
            session.get("workspace_path", ""),
            session.get("start_time", ""),
            session.get("end_time", ""),
            session.get("duration_minutes", 0),
        ))
        self.conn.commit()

    def get_project_sessions(self, date, project_name=None):
        """获取项目会话，可按项目名筛选"""
        cursor = self.conn.cursor()
        if project_name:
            cursor.execute(
                "SELECT * FROM project_sessions WHERE substr(start_time, 1, 10) = ? AND project_name = ?",
                (date, project_name)
            )
        else:
            cursor.execute(
                "SELECT * FROM project_sessions WHERE substr(start_time, 1, 10) = ?",
                (date,)
            )
        return [self._row_to_proj_dict(row) for row in cursor.fetchall()]

    def _row_to_proj_dict(self, row):
        """将项目会话 Row 转换为字典"""
        return {
            "project_name": row["project_name"],
            "app_name": row["app_name"],
            "workspace_path": row["workspace_path"],
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "duration_minutes": row["duration_minutes"],
        }

    # --- Focus Sessions ---

    def save_focus_session(self, session):
        """保存专注会话"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO focus_sessions
            (date, duration_minutes, timestamp, app_name, category)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session.get("date", ""),
            session.get("duration_minutes", session.get("duration", 0)),
            session.get("timestamp", ""),
            session.get("app_name", ""),
            session.get("category", ""),
        ))
        self.conn.commit()

    def get_focus_sessions(self, date=None):
        """获取专注会话"""
        cursor = self.conn.cursor()
        if date:
            cursor.execute(
                "SELECT * FROM focus_sessions WHERE date = ?",
                (date,)
            )
        else:
            cursor.execute("SELECT * FROM focus_sessions")
        return [self._row_to_focus_dict(row) for row in cursor.fetchall()]

    def _row_to_focus_dict(self, row):
        """将专注会话 Row 转换为字典"""
        return {
            "date": row["date"],
            "duration_minutes": row["duration_minutes"],
            "timestamp": row["timestamp"],
            "app_name": row["app_name"],
            "category": row["category"],
        }

    # --- 通用查询 ---

    def query(self, table, filters=None, order_by=None, limit=None):
        """通用查询接口"""
        allowed_tables = {
            "usage_records", "foreground_sessions", "focus_sessions",
            "context_switches", "project_sessions"
        }
        if table not in allowed_tables:
            raise ValueError(f"不支持的表名: {table}")

        sql = f"SELECT * FROM {table}"
        params = []

        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(f"{key} = ?")
                params.append(value)
            sql += " WHERE " + " AND ".join(conditions)

        if order_by:
            # 简单防注入：只允许字母、下划线和空格（用于 ASC/DESC）
            safe_order = "".join(c for c in order_by if c.isalnum() or c in "_ ")
            sql += f" ORDER BY {safe_order}"

        if limit:
            sql += f" LIMIT {int(limit)}"

        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()


class JSONBackend:
    """JSON 文件存储后端，兼容 V1 数据格式"""

    def __init__(self, data_dir=None):
        """
        Args:
            data_dir: 数据目录路径，默认为 data/
        """
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # --- 内部工具方法 ---

    def _usage_file(self, date):
        """获取指定日期的使用数据文件路径"""
        return self.data_dir / f"usage_{date}.json"

    def _load_usage_file(self, date):
        """加载指定日期的使用数据文件，兼容 V1 格式"""
        filepath = self._usage_file(date)
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                print(f"⚠️ 数据文件格式错误: {filepath}")
        return {"date": date, "records": []}

    def _save_usage_file(self, date, data):
        """保存使用数据文件，保持 V1 兼容格式"""
        filepath = self._usage_file(date)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_json_file(self, filepath, default=None):
        """通用 JSON 文件加载"""
        if default is None:
            default = []
        filepath = Path(filepath)
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return default

    def _save_json_file(self, filepath, data):
        """通用 JSON 文件保存"""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # --- Usage Records ---

    def save_usage_records(self, records, date):
        """保存使用记录（追加模式），保持 V1 兼容格式 {"date": "...", "records": [...]}"""
        data = self._load_usage_file(date)
        for r in records:
            # 统一字段名为 V1 格式（大写开头）
            record = {
                "timestamp": r.get("timestamp", ""),
                "hour": r.get("hour", 0),
                "Name": r.get("Name", r.get("name", "")),
                "Category": r.get("Category", r.get("category", "其他")),
                "CPU": r.get("CPU", r.get("cpu", 0)),
                "MemoryMB": r.get("MemoryMB", r.get("memory_mb", 0)),
                "DurationMinutes": r.get("DurationMinutes", r.get("duration_minutes", 0)),
                "is_foreground": r.get("is_foreground", 0),
                "foreground_minutes": r.get("foreground_minutes", 0),
                "device_id": r.get("device_id", "local"),
            }
            data["records"].append(record)
        self._save_usage_file(date, data)

    def get_usage_records(self, date):
        """获取指定日期的使用记录"""
        data = self._load_usage_file(date)
        return [self._normalize_usage_record(r) for r in data.get("records", [])]

    def get_usage_records_range(self, start_date, end_date):
        """获取日期范围内的使用记录"""
        from datetime import datetime, timedelta
        results = []
        current = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            results.extend(self.get_usage_records(date_str))
            current += timedelta(days=1)
        return results

    def _normalize_usage_record(self, r):
        """标准化使用记录字段名，同时保留 V1 和 V2 格式"""
        return {
            "timestamp": r.get("timestamp", ""),
            "hour": r.get("hour", 0),
            "name": r.get("Name", r.get("name", "")),
            "Name": r.get("Name", r.get("name", "")),
            "category": r.get("Category", r.get("category", "其他")),
            "Category": r.get("Category", r.get("category", "其他")),
            "cpu": r.get("CPU", r.get("cpu", 0)),
            "CPU": r.get("CPU", r.get("cpu", 0)),
            "memory_mb": r.get("MemoryMB", r.get("memory_mb", 0)),
            "MemoryMB": r.get("MemoryMB", r.get("memory_mb", 0)),
            "duration_minutes": r.get("DurationMinutes", r.get("duration_minutes", 0)),
            "DurationMinutes": r.get("DurationMinutes", r.get("duration_minutes", 0)),
            "is_foreground": r.get("is_foreground", 0),
            "foreground_minutes": r.get("foreground_minutes", 0),
            "device_id": r.get("device_id", "local"),
        }

    # --- Foreground Sessions ---

    def save_foreground_session(self, session):
        """保存一条前台会话到 data/foreground_YYYY-MM-DD.json"""
        date = session.get("start_time", "")[:10]
        filepath = self.data_dir / f"foreground_{date}.json"
        data = self._load_json_file(filepath, default=[])
        data.append(session)
        self._save_json_file(filepath, data)

    def get_foreground_sessions(self, date):
        """获取指定日期的前台会话"""
        filepath = self.data_dir / f"foreground_{date}.json"
        return self._load_json_file(filepath, default=[])

    # --- Context Switches ---

    def save_context_switch(self, switch):
        """保存一条切换事件到 data/switches_YYYY-MM-DD.json"""
        date = switch.get("timestamp", "")[:10]
        filepath = self.data_dir / f"switches_{date}.json"
        data = self._load_json_file(filepath, default=[])
        data.append(switch)
        self._save_json_file(filepath, data)

    def get_context_switches(self, date):
        """获取指定日期的切换事件"""
        filepath = self.data_dir / f"switches_{date}.json"
        return self._load_json_file(filepath, default=[])

    # --- Project Sessions ---

    def save_project_session(self, session):
        """保存一条项目会话到 data/projects_YYYY-MM-DD.json"""
        date = session.get("start_time", "")[:10]
        filepath = self.data_dir / f"projects_{date}.json"
        data = self._load_json_file(filepath, default=[])
        data.append(session)
        self._save_json_file(filepath, data)

    def get_project_sessions(self, date, project_name=None):
        """获取项目会话，可按项目名筛选"""
        filepath = self.data_dir / f"projects_{date}.json"
        sessions = self._load_json_file(filepath, default=[])
        if project_name:
            sessions = [s for s in sessions if s.get("project_name") == project_name]
        return sessions

    # --- Focus Sessions ---

    def save_focus_session(self, session):
        """保存专注会话到 data/focus_sessions.json"""
        filepath = self.data_dir / "focus_sessions.json"
        data = self._load_json_file(filepath, default={"sessions": [], "daily_stats": {}})
        # 兼容 V1 格式
        if isinstance(data, dict) and "sessions" in data:
            data["sessions"].append(session)
        else:
            # 如果是列表格式，直接追加
            if isinstance(data, list):
                data.append(session)
            else:
                data = {"sessions": [session], "daily_stats": {}}
        self._save_json_file(filepath, data)

    def get_focus_sessions(self, date=None):
        """获取专注会话"""
        filepath = self.data_dir / "focus_sessions.json"
        data = self._load_json_file(filepath, default={"sessions": [], "daily_stats": {}})
        # 兼容 V1 格式
        if isinstance(data, dict) and "sessions" in data:
            sessions = data["sessions"]
        elif isinstance(data, list):
            sessions = data
        else:
            sessions = []
        if date:
            sessions = [s for s in sessions if s.get("date") == date]
        return sessions

    # --- 通用查询 ---

    def query(self, table, filters=None, order_by=None, limit=None):
        """
        通用查询接口（JSON 后端仅支持基础筛选）
        注意：JSON 后端的 query 功能有限，复杂查询建议使用 SQLite 后端
        """
        # 根据表名加载对应数据
        if table == "usage_records":
            # 需要遍历所有日期文件
            records = self._get_all_usage_records()
        elif table == "foreground_sessions":
            records = self._get_all_dated_records("foreground_")
        elif table == "context_switches":
            records = self._get_all_dated_records("switches_")
        elif table == "project_sessions":
            records = self._get_all_dated_records("projects_")
        elif table == "focus_sessions":
            records = self.get_focus_sessions()
        else:
            raise ValueError(f"不支持的表名: {table}")

        # 应用筛选
        if filters:
            for key, value in filters.items():
                records = [r for r in records if r.get(key) == value]

        # 应用排序
        if order_by:
            # 解析排序字段和方向
            parts = order_by.strip().split()
            field = parts[0]
            reverse = len(parts) > 1 and parts[1].upper() == "DESC"
            records.sort(key=lambda r: r.get(field, ""), reverse=reverse)

        # 应用限制
        if limit:
            records = records[:int(limit)]

        return records

    def _get_all_usage_records(self):
        """获取所有日期的使用记录"""
        records = []
        for filepath in sorted(self.data_dir.glob("usage_*.json")):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for r in data.get("records", []):
                    records.append(self._normalize_usage_record(r))
            except (json.JSONDecodeError, IOError):
                continue
        return records

    def _get_all_dated_records(self, prefix):
        """获取所有带日期前缀的 JSON 文件中的记录"""
        records = []
        for filepath in sorted(self.data_dir.glob(f"{prefix}*.json")):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    records.extend(data)
            except (json.JSONDecodeError, IOError):
                continue
        return records

    def close(self):
        """JSON 后端无需关闭操作"""
        pass


class DataStore:
    """统一数据访问接口，支持 JSON 和 SQLite 双后端"""

    def __init__(self, backend=None, db_path=None, data_dir=None):
        """
        Args:
            backend: "sqlite" 或 "json"，默认从 config.json 的 storage_backend 读取
            db_path: SQLite 数据库文件路径（仅 sqlite 后端使用）
            data_dir: JSON 数据目录路径（仅 json 后端使用）
        """
        if backend is None:
            config = load_config()
            backend = config.get("storage_backend", "sqlite")

        self.backend_type = backend

        if backend == "sqlite":
            self._backend = SQLiteBackend(db_path=db_path)
        elif backend == "json":
            self._backend = JSONBackend(data_dir=data_dir)
        else:
            raise ValueError(f"不支持的存储后端: {backend}，请使用 'sqlite' 或 'json'")

    # --- Usage Records ---

    def save_usage_records(self, records, date):
        """保存使用记录（追加模式）"""
        self._backend.save_usage_records(records, date)

    def get_usage_records(self, date):
        """获取指定日期的使用记录"""
        return self._backend.get_usage_records(date)

    def get_usage_records_range(self, start_date, end_date):
        """获取日期范围内的使用记录"""
        return self._backend.get_usage_records_range(start_date, end_date)

    # --- Foreground Sessions ---

    def save_foreground_session(self, session):
        """保存一条前台会话"""
        self._backend.save_foreground_session(session)

    def get_foreground_sessions(self, date):
        """获取指定日期的前台会话"""
        return self._backend.get_foreground_sessions(date)

    # --- Context Switches ---

    def save_context_switch(self, switch):
        """保存一条切换事件"""
        self._backend.save_context_switch(switch)

    def get_context_switches(self, date):
        """获取指定日期的切换事件"""
        return self._backend.get_context_switches(date)

    # --- Project Sessions ---

    def save_project_session(self, session):
        """保存一条项目会话"""
        self._backend.save_project_session(session)

    def get_project_sessions(self, date, project_name=None):
        """获取项目会话，可按项目名筛选"""
        return self._backend.get_project_sessions(date, project_name)

    # --- Focus Sessions ---

    def save_focus_session(self, session):
        """保存专注会话"""
        self._backend.save_focus_session(session)

    def get_focus_sessions(self, date=None):
        """获取专注会话"""
        return self._backend.get_focus_sessions(date)

    # --- 通用查询 ---

    def query(self, table, filters=None, order_by=None, limit=None):
        """通用查询接口（仅 SQLite 后端完整支持）"""
        return self._backend.query(table, filters=filters, order_by=order_by, limit=limit)

    def close(self):
        """关闭后端连接"""
        self._backend.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
