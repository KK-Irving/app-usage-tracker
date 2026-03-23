# -*- coding: utf-8 -*-
"""
db_migrate.py 单元测试
验证 JSON → SQLite 迁移工具的核心功能和 DataStore 基本操作
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.data_store import DataStore
from scripts.db_migrate import load_usage_json, load_focus_sessions, migrate
from scripts import db_migrate
from scripts import data_store as data_store_mod


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """创建临时数据目录并 patch DATA_DIR"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(db_migrate, "DATA_DIR", data_dir)
    monkeypatch.setattr(data_store_mod, "DATA_DIR", data_dir)
    return data_dir


class TestLoadUsageJson:
    def test_valid_file(self, tmp_path):
        f = tmp_path / "usage_2026-01-01.json"
        f.write_text(json.dumps({"date": "2026-01-01", "records": [{"Name": "test"}]}), encoding="utf-8")
        date, records = load_usage_json(f)
        assert date == "2026-01-01"
        assert len(records) == 1

    def test_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not json", encoding="utf-8")
        date, records = load_usage_json(f)
        assert date is None
        assert records == []

    def test_empty_records(self, tmp_path):
        f = tmp_path / "usage_2026-01-02.json"
        f.write_text(json.dumps({"date": "2026-01-02", "records": []}), encoding="utf-8")
        date, records = load_usage_json(f)
        assert date == "2026-01-02"
        assert records == []


class TestLoadFocusSessions:
    def test_no_file(self, tmp_data_dir):
        sessions = load_focus_sessions()
        assert sessions == []

    def test_dict_format(self, tmp_data_dir):
        f = tmp_data_dir / "focus_sessions.json"
        f.write_text(json.dumps({"sessions": [{"date": "2026-01-01", "duration": 25}], "daily_stats": {}}), encoding="utf-8")
        sessions = load_focus_sessions()
        assert len(sessions) == 1

    def test_list_format(self, tmp_data_dir):
        f = tmp_data_dir / "focus_sessions.json"
        f.write_text(json.dumps([{"date": "2026-01-01", "duration": 25}]), encoding="utf-8")
        sessions = load_focus_sessions()
        assert len(sessions) == 1


class TestMigrate:
    def test_dry_run(self, tmp_data_dir, capsys):
        f = tmp_data_dir / "usage_2026-01-01.json"
        f.write_text(json.dumps({
            "date": "2026-01-01",
            "records": [{"timestamp": "2026-01-01 10:00:00", "hour": 10, "Name": "test", "Category": "开发",
                         "CPU": 1.0, "MemoryMB": 100, "DurationMinutes": 30}]
        }), encoding="utf-8")
        migrate(dry_run=True)
        output = capsys.readouterr().out
        assert "dry-run" in output.lower() or "预览" in output

    def test_actual_migrate(self, tmp_data_dir):
        f = tmp_data_dir / "usage_2026-01-01.json"
        f.write_text(json.dumps({
            "date": "2026-01-01",
            "records": [{"timestamp": "2026-01-01 10:00:00", "hour": 10, "Name": "code.exe", "Category": "开发",
                         "CPU": 5.0, "MemoryMB": 200, "DurationMinutes": 60}]
        }), encoding="utf-8")
        migrate(dry_run=False)
        # Verify data was written to SQLite
        store = DataStore(backend="sqlite", db_path=tmp_data_dir / "usage_tracker.db")
        records = store.get_usage_records("2026-01-01")
        assert len(records) >= 1
        assert records[0]["name"] == "code.exe"
        store.close()


class TestDataStoreRoundTrip:
    def test_sqlite_usage_round_trip(self, tmp_path):
        store = DataStore(backend="sqlite", db_path=tmp_path / "test.db")
        record = {
            "timestamp": "2026-01-01 12:00:00", "hour": 12,
            "name": "python.exe", "category": "开发",
            "cpu": 10.5, "memory_mb": 256.0, "duration_minutes": 45.0,
            "is_foreground": 1, "foreground_minutes": 30.0, "device_id": "local"
        }
        store.save_usage_records([record], "2026-01-01")
        results = store.get_usage_records("2026-01-01")
        assert len(results) == 1
        assert results[0]["name"] == "python.exe"
        assert results[0]["cpu"] == pytest.approx(10.5)
        assert results[0]["is_foreground"] == 1
        store.close()

    def test_json_usage_round_trip(self, tmp_path):
        store = DataStore(backend="json", data_dir=tmp_path)
        record = {
            "timestamp": "2026-01-01 12:00:00", "hour": 12,
            "Name": "chrome.exe", "Category": "工作",
            "CPU": 5.0, "MemoryMB": 128.0, "DurationMinutes": 20.0
        }
        store.save_usage_records([record], "2026-01-01")
        results = store.get_usage_records("2026-01-01")
        assert len(results) == 1
        assert results[0]["Name"] == "chrome.exe"
        store.close()

    def test_foreground_session_round_trip(self, tmp_path):
        store = DataStore(backend="sqlite", db_path=tmp_path / "test.db")
        session = {
            "app_name": "code.exe", "window_title": "main.py - project",
            "start_time": "2026-01-01 10:00:00", "end_time": "2026-01-01 10:30:00",
            "duration_seconds": 1800.0
        }
        store.save_foreground_session(session)
        results = store.get_foreground_sessions("2026-01-01")
        assert len(results) == 1
        assert results[0]["app_name"] == "code.exe"
        assert results[0]["duration_seconds"] == 1800.0
        store.close()

    def test_context_switch_round_trip(self, tmp_path):
        store = DataStore(backend="sqlite", db_path=tmp_path / "test.db")
        switch = {"timestamp": "2026-01-01 10:15:00", "from_app": "code.exe", "to_app": "chrome.exe"}
        store.save_context_switch(switch)
        results = store.get_context_switches("2026-01-01")
        assert len(results) == 1
        assert results[0]["from_app"] == "code.exe"
        store.close()

    def test_focus_session_round_trip(self, tmp_path):
        store = DataStore(backend="sqlite", db_path=tmp_path / "test.db")
        session = {"date": "2026-01-01", "duration_minutes": 25.0, "timestamp": "2026-01-01 10:00:00",
                    "app_name": "code.exe", "category": "开发"}
        store.save_focus_session(session)
        results = store.get_focus_sessions("2026-01-01")
        assert len(results) == 1
        assert results[0]["duration_minutes"] == 25.0
        store.close()

    def test_project_session_round_trip(self, tmp_path):
        store = DataStore(backend="sqlite", db_path=tmp_path / "test.db")
        session = {"project_name": "myproject", "app_name": "code.exe", "workspace_path": "/projects/myproject",
                    "start_time": "2026-01-01 10:00:00", "end_time": "2026-01-01 11:00:00", "duration_minutes": 60.0}
        store.save_project_session(session)
        results = store.get_project_sessions("2026-01-01")
        assert len(results) == 1
        assert results[0]["project_name"] == "myproject"
        store.close()
