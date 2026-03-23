# -*- coding: utf-8 -*-
"""
系统托盘常驻 (TrayApp)
通过 pystray 在系统托盘显示图标，实时显示使用信息
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

try:
    import pystray
    from PIL import Image, ImageDraw
    _pystray_available = True
except ImportError:
    _pystray_available = False


def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _create_icon_image():
    """创建一个简单的托盘图标"""
    img = Image.new('RGB', (64, 64), color=(44, 62, 80))
    draw = ImageDraw.Draw(img)
    draw.rectangle([16, 16, 48, 48], fill=(52, 152, 219))
    draw.rectangle([24, 24, 40, 40], fill=(255, 255, 255))
    return img


class TrayApp:
    """系统托盘常驻应用"""

    def __init__(self, data_store, foreground_detector, break_reminder):
        self.data_store = data_store
        self.fg = foreground_detector
        self.brk = break_reminder
        self._icon = None
        config = load_config()
        self._refresh_interval = config.get("tray_refresh_seconds", 60)
        self._collect_interval = config.get("interval_minutes", 60) * 60
        self._running = False
        self._tooltip_thread = None
        self._collect_thread = None

    def start(self):
        """启动托盘应用"""
        if not _pystray_available:
            print("❌ pystray 未安装。安装: pip install pystray Pillow")
            return

        config = load_config()
        if not config.get("tray_enabled", True):
            print("⚠️ 系统托盘已禁用 (tray_enabled=false)")
            return

        self._running = True

        # 启动后台服务
        self.fg.start()
        self.brk.start()

        # 启动 tooltip 刷新线程
        self._tooltip_thread = threading.Thread(target=self._tooltip_loop, daemon=True)
        self._tooltip_thread.start()

        # 启动数据采集定时器
        self._collect_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self._collect_thread.start()

        # 创建托盘图标
        self._icon = pystray.Icon(
            "AppUsageTracker",
            _create_icon_image(),
            "App Usage Tracker",
            menu=self._create_menu(),
        )
        self._icon.run()

    def stop(self):
        """安全停止所有后台任务并退出"""
        self._running = False
        self.brk.stop()
        self.fg.stop()
        if self._icon:
            self._icon.stop()

    def _create_menu(self):
        """创建右键菜单"""
        return pystray.Menu(
            pystray.MenuItem("查看今日报告", self._on_daily_report),
            pystray.MenuItem("打开 Web 仪表盘", self._on_open_web),
            pystray.MenuItem("手动采集", self._on_manual_collect),
            pystray.MenuItem("设置", self._on_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._on_quit),
        )

    def _on_left_click(self):
        """左键点击：显示今日概况"""
        today = datetime.now().strftime("%Y-%m-%d")
        records = self.data_store.get_usage_records(today)
        total = sum(r.get("duration_minutes", r.get("DurationMinutes", 0)) for r in records)
        hrs = int(total // 60)
        mins = int(total % 60)

        # 简单弹窗
        try:
            from scripts.timeout_alert import send_notification
            # Top 3 应用
            app_mins = {}
            for r in records:
                name = r.get("name", r.get("Name", ""))
                app_mins[name] = app_mins.get(name, 0) + r.get("duration_minutes", r.get("DurationMinutes", 0))
            top3 = sorted(app_mins.items(), key=lambda x: x[1], reverse=True)[:3]
            top3_str = ", ".join(f"{n}({int(m)}m)" for n, m in top3)
            send_notification("📊 今日概况", f"总时长: {hrs}h {mins}m\nTop 3: {top3_str}")
        except Exception:
            pass

    def _on_daily_report(self, icon=None, item=None):
        """查看今日报告"""
        try:
            from scripts.get_daily_report import generate_report
            report = generate_report()
            if report:
                print(report)
        except Exception as e:
            print(f"生成报告失败: {e}")

    def _on_open_web(self, icon=None, item=None):
        """打开 Web 仪表盘"""
        import webbrowser
        config = load_config()
        host = config.get("web_host", "127.0.0.1")
        port = config.get("web_port", 8080)
        webbrowser.open(f"http://{host}:{port}")

    def _on_manual_collect(self, icon=None, item=None):
        """手动采集"""
        try:
            from scripts.collect_usage import collect
            collect(foreground_detector=self.fg)
        except Exception as e:
            print(f"采集失败: {e}")

    def _on_settings(self, icon=None, item=None):
        """打开设置"""
        import os
        os.startfile(str(CONFIG_FILE))

    def _on_quit(self, icon=None, item=None):
        """退出"""
        self.stop()

    def _update_tooltip(self):
        """更新 tooltip"""
        if not self._icon:
            return
        fg = self.fg.get_current_foreground()
        app_name = fg["app_name"] if fg else "无"
        today = datetime.now().strftime("%Y-%m-%d")
        records = self.data_store.get_usage_records(today)
        total = sum(r.get("duration_minutes", r.get("DurationMinutes", 0)) for r in records)
        hrs = int(total // 60)
        mins = int(total % 60)
        self._icon.title = f"当前: {app_name} | 今日: {hrs}h{mins}m"

    def _tooltip_loop(self):
        """tooltip 刷新循环"""
        while self._running:
            try:
                self._update_tooltip()
            except Exception:
                pass
            time.sleep(self._refresh_interval)

    def _collection_loop(self):
        """数据采集定时循环"""
        while self._running:
            time.sleep(self._collect_interval)
            try:
                from scripts.collect_usage import collect
                collect(foreground_detector=self.fg)
            except Exception:
                pass
