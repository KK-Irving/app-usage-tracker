# -*- coding: utf-8 -*-
"""
前台窗口检测器 (ForegroundDetector)
通过 win32gui 轮询前台窗口，记录前台会话和切换事件
"""
import json
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

ROOT_DIR = Path(__file__).parent.parent
CONFIG_FILE = ROOT_DIR / "config.json"

# 尝试导入 win32gui
_win32gui_available = False
try:
    import win32gui
    import win32process
    import psutil
    _win32gui_available = True
except ImportError:
    pass


def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


class ForegroundDetector:
    """前台窗口检测器，通过 win32gui 轮询前台窗口"""

    def __init__(self, data_store, interval=None):
        """
        Args:
            data_store: DataStore 实例
            interval: 采样间隔（秒），默认从 config.json 读取，否则 1 秒
        """
        self.data_store = data_store
        if interval is None:
            config = load_config()
            interval = config.get("foreground_interval_seconds", 1.0)
        self.interval = interval
        self._current_session = None
        self._running = False
        self._thread = None
        self._warned = False

    @property
    def win32gui_available(self):
        return _win32gui_available

    def get_foreground_window(self):
        """
        获取当前前台窗口信息
        Returns:
            (进程名称, 窗口标题) 或 None
        """
        if not _win32gui_available:
            if not self._warned:
                print("⚠️ pywin32 未安装，前台检测不可用。安装: pip install pywin32")
                self._warned = True
            return None

        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None
            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid <= 0:
                return None
            proc = psutil.Process(pid)
            return (proc.name(), title)
        except Exception:
            return None

    def start(self):
        """在后台线程中启动前台检测循环"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止检测循环，保存当前未结束的会话"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=self.interval + 1)
            self._thread = None
        # 保存当前未结束的会话
        if self._current_session:
            self._end_current_session()

    def _poll_loop(self):
        """轮询循环核心逻辑"""
        while self._running:
            result = self.get_foreground_window()
            if result is not None:
                app_name, window_title = result
                if self._current_session is None:
                    # 首次检测，创建新会话
                    self._current_session = {
                        "app_name": app_name,
                        "window_title": window_title,
                        "start_time": datetime.now().isoformat(),
                        "duration_seconds": 0,
                    }
                elif (self._current_session["app_name"] != app_name or
                      self._current_session["window_title"] != window_title):
                    # 窗口变化，触发切换
                    self._on_window_change(app_name, window_title)
                else:
                    # 窗口不变，累加时长
                    self._current_session["duration_seconds"] += self.interval
            time.sleep(self.interval)

    def _on_window_change(self, app_name, window_title):
        """窗口切换处理"""
        now = datetime.now().isoformat()
        old_session = self._current_session

        if old_session:
            # 结束当前会话
            old_session["end_time"] = now
            self.data_store.save_foreground_session(old_session)

            # 记录切换事件
            self.data_store.save_context_switch({
                "timestamp": now,
                "from_app": old_session["app_name"],
                "to_app": app_name,
            })

        # 创建新会话
        self._current_session = {
            "app_name": app_name,
            "window_title": window_title,
            "start_time": now,
            "duration_seconds": 0,
        }

    def _end_current_session(self):
        """结束并保存当前会话"""
        if self._current_session:
            self._current_session["end_time"] = datetime.now().isoformat()
            self.data_store.save_foreground_session(self._current_session)
            self._current_session = None

    def get_current_foreground(self):
        """获取当前前台应用信息（供 TrayApp tooltip 使用）"""
        if self._current_session:
            return {
                "app_name": self._current_session["app_name"],
                "window_title": self._current_session["window_title"],
                "duration_seconds": self._current_session["duration_seconds"],
            }
        return None
