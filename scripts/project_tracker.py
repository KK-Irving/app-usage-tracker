# -*- coding: utf-8 -*-
"""
项目级时间追踪 (ProjectTracker)
将应用使用时间归属到具体项目，支持 VS Code 窗口标题解析和路径匹配
"""
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import psutil
    _psutil_available = True
except ImportError:
    _psutil_available = False

ROOT_DIR = Path(__file__).parent.parent
CONFIG_DIR = ROOT_DIR / "config"

UNCATEGORIZED = "未分类项目"


class ProjectTracker:
    CONFIG_PATH = CONFIG_DIR / "projects.json"

    def __init__(self, data_store, foreground_detector=None):
        self.data_store = data_store
        self.fg = foreground_detector
        self._projects = {}
        self.load_projects()

    def load_projects(self):
        """从 config/projects.json 加载项目映射"""
        if self.CONFIG_PATH.exists():
            try:
                with open(self.CONFIG_PATH, 'r', encoding='utf-8') as f:
                    self._projects = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._projects = {}
        return self._projects

    def save_projects(self):
        self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(self._projects, f, ensure_ascii=False, indent=2)

    def add_project(self, name, path):
        """注册项目"""
        self._projects[name] = path
        self.save_projects()

    def remove_project(self, name):
        """移除项目"""
        if name in self._projects:
            del self._projects[name]
            self.save_projects()
            return True
        return False

    def list_projects(self):
        """列出所有已注册项目"""
        return dict(self._projects)

    def detect_project(self, app_name, window_title):
        """
        检测当前活动属于哪个项目
        策略:
        1. VS Code: 从窗口标题提取项目名
        2. 终端: 通过 psutil.Process.cwd()
        3. 匹配已注册项目的路径前缀（最长前缀匹配）
        4. 未匹配返回 "未分类项目"
        """
        # VS Code 窗口标题解析: "文件名 - 项目名 - Visual Studio Code"
        if app_name and app_name.lower() in ("code.exe", "code"):
            project_name = self._parse_vscode_title(window_title)
            if project_name:
                # 尝试匹配已注册项目
                for name, path in self._projects.items():
                    if project_name.lower() == name.lower():
                        return name
                return project_name

        # 终端: 尝试获取 cwd
        if app_name and app_name.lower() in ("powershell.exe", "cmd.exe", "bash.exe", "wt.exe"):
            cwd = self._get_terminal_cwd(app_name)
            if cwd:
                matched = self._match_project_path(cwd)
                if matched:
                    return matched

        # 通用路径匹配（从窗口标题提取路径信息）
        return UNCATEGORIZED

    @staticmethod
    def _parse_vscode_title(title):
        """
        解析 VS Code 窗口标题，提取项目名
        格式: "文件名 - 项目名 - Visual Studio Code"
        或: "项目名 - Visual Studio Code"
        """
        if not title:
            return None
        # 移除 " - Visual Studio Code" 后缀
        suffix = " - Visual Studio Code"
        if title.endswith(suffix):
            rest = title[:-len(suffix)]
            parts = rest.rsplit(" - ", 1)
            if len(parts) == 2:
                return parts[1].strip()
            elif len(parts) == 1:
                return parts[0].strip()
        return None

    def _get_terminal_cwd(self, app_name):
        """通过 psutil 获取终端进程的 cwd"""
        if not _psutil_available:
            return None
        try:
            for proc in psutil.process_iter(['name', 'pid']):
                if proc.info['name'] and proc.info['name'].lower() == app_name.lower():
                    try:
                        return proc.cwd()
                    except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                        continue
        except Exception:
            pass
        return None

    def _match_project_path(self, path):
        """最长前缀匹配已注册项目"""
        path = path.replace("\\", "/").rstrip("/").lower()
        best_match = None
        best_len = 0
        for name, proj_path in self._projects.items():
            pp = proj_path.replace("\\", "/").rstrip("/").lower()
            if path.startswith(pp) and len(pp) > best_len:
                best_match = name
                best_len = len(pp)
        return best_match

    def get_project_report(self, date):
        """获取项目时间分布"""
        sessions = self.data_store.get_project_sessions(date)
        project_minutes = {}
        for s in sessions:
            name = s.get("project_name", UNCATEGORIZED)
            project_minutes[name] = project_minutes.get(name, 0) + s.get("duration_minutes", 0)

        total = sum(project_minutes.values())
        return [
            {"name": name, "minutes": mins, "pct": (mins / total * 100) if total > 0 else 0}
            for name, mins in sorted(project_minutes.items(), key=lambda x: x[1], reverse=True)
        ]

    def get_project_report_range(self, start_date, end_date):
        """获取日期范围内的项目时间汇总"""
        current = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        project_minutes = {}
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            sessions = self.data_store.get_project_sessions(date_str)
            for s in sessions:
                name = s.get("project_name", UNCATEGORIZED)
                project_minutes[name] = project_minutes.get(name, 0) + s.get("duration_minutes", 0)
            current += timedelta(days=1)

        total = sum(project_minutes.values())
        return [
            {"name": name, "minutes": mins, "pct": (mins / total * 100) if total > 0 else 0}
            for name, mins in sorted(project_minutes.items(), key=lambda x: x[1], reverse=True)
        ]
