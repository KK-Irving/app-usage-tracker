# -*- coding: utf-8 -*-
"""
休息提醒 (BreakReminder)
在连续工作一段时间后提醒用户休息，支持 20-20-20 法则和自定义规则
"""
import json
import sys
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app_categories import classify_app

ROOT_DIR = Path(__file__).parent.parent
CONFIG_DIR = ROOT_DIR / "config"

WORK_CATEGORIES = {"工作", "开发"}


@dataclass
class BreakRule:
    work_threshold_minutes: float
    break_duration_minutes: float
    reminder_message: str


class BreakReminder:
    CONFIG_PATH = CONFIG_DIR / "break_rules.json"

    DEFAULT_RULES = [
        BreakRule(20, 0.33, "👀 20-20-20: 休息20秒，注视6米外的物体"),
        BreakRule(90, 10, "🚶 连续工作90分钟，建议休息10分钟"),
    ]

    def __init__(self, foreground_detector):
        self.fg = foreground_detector
        self._rules = []
        self._work_start_times = {}  # rule_index → work_start_time
        self._running = False
        self._thread = None
        self._notified = set()  # 已通知的规则索引，避免重复
        self.load_rules()

    def load_rules(self):
        """从 config/break_rules.json 加载规则"""
        if self.CONFIG_PATH.exists():
            try:
                with open(self.CONFIG_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._rules = [BreakRule(**r) for r in data]
            except (json.JSONDecodeError, IOError, TypeError):
                self._rules = list(self.DEFAULT_RULES)
        else:
            self._rules = list(self.DEFAULT_RULES)
        return self._rules

    def save_rules(self):
        self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump([asdict(r) for r in self._rules], f, ensure_ascii=False, indent=2)

    def add_rule(self, threshold, duration, message):
        """添加休息规则"""
        self._rules.append(BreakRule(
            work_threshold_minutes=float(threshold),
            break_duration_minutes=float(duration),
            reminder_message=message,
        ))
        self.save_rules()

    def list_rules(self):
        return list(self._rules)

    def start(self):
        """在后台线程中启动休息提醒监控"""
        if self._running:
            return
        self._running = True
        self._work_start_times = {}
        self._notified = set()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            current = self.fg.get_current_foreground()
            now = time.time()

            if current:
                app_name = current.get("app_name", "")
                cat, _ = classify_app(app_name)
                is_work = cat in WORK_CATEGORIES

                if is_work:
                    # 工作中：检查每条规则
                    for i, rule in enumerate(self._rules):
                        if i not in self._work_start_times:
                            self._work_start_times[i] = now
                        elapsed = (now - self._work_start_times[i]) / 60
                        if elapsed >= rule.work_threshold_minutes and i not in self._notified:
                            self._send_reminder(rule)
                            self._notified.add(i)
                else:
                    # 非工作：检查是否满足休息时长，满足则重置
                    for i, rule in enumerate(self._rules):
                        if i in self._work_start_times:
                            # 简化：切换到非工作类即开始计算休息
                            # 如果持续非工作超过 break_duration，重置
                            self._reset_timer(i)

            time.sleep(10)  # 每 10 秒检查一次

    def _send_reminder(self, rule):
        """发送 Windows Toast 通知"""
        try:
            from scripts.timeout_alert import send_notification
            send_notification("⏰ 休息提醒", rule.reminder_message)
        except ImportError:
            print(f"🔔 {rule.reminder_message}")

    def _reset_timer(self, rule_index):
        """重置指定规则的工作计时器"""
        if rule_index in self._work_start_times:
            del self._work_start_times[rule_index]
        self._notified.discard(rule_index)
