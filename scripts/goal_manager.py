# -*- coding: utf-8 -*-
"""
目标设定与达成率管理 (GoalManager)
支持按分类或应用设定每日使用目标，评估达成率和趋势
"""
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

ROOT_DIR = Path(__file__).parent.parent
CONFIG_DIR = ROOT_DIR / "config"


@dataclass
class UsageGoal:
    target: str       # 分类名（如"开发"）或应用名（如"chrome"）
    goal_type: str    # "min"（下限）或 "max"（上限）
    minutes: float    # 目标时长（分钟）


class GoalManager:
    CONFIG_PATH = CONFIG_DIR / "usage_goals.json"

    def __init__(self, data_store):
        self.data_store = data_store
        self._goals = []
        self.load_goals()

    def load_goals(self):
        """从 config/usage_goals.json 加载目标列表"""
        if self.CONFIG_PATH.exists():
            try:
                with open(self.CONFIG_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._goals = [UsageGoal(**g) for g in data]
            except (json.JSONDecodeError, IOError, TypeError):
                self._goals = []
        else:
            self._goals = []
        return self._goals

    def save_goals(self):
        """持久化目标列表到 JSON"""
        self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump([asdict(g) for g in self._goals], f, ensure_ascii=False, indent=2)

    def add_goal(self, target, goal_type, minutes):
        """添加一条目标"""
        goal = UsageGoal(target=target, goal_type=goal_type, minutes=float(minutes))
        self._goals.append(goal)
        self.save_goals()

    def remove_goal(self, target):
        """按 target 名称移除目标"""
        before = len(self._goals)
        self._goals = [g for g in self._goals if g.target != target]
        if len(self._goals) < before:
            self.save_goals()
            return True
        return False

    def list_goals(self):
        """返回所有目标"""
        return list(self._goals)

    def evaluate(self, date=None):
        """
        评估指定日期的目标达成率
        Returns: [{"goal": UsageGoal, "actual_minutes": float,
                   "achievement_rate": float, "achieved": bool}]
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        records = self.data_store.get_usage_records(date)
        # 按分类和应用名汇总时长
        category_minutes = {}
        app_minutes = {}
        for r in records:
            cat = r.get("category", r.get("Category", "其他"))
            name = r.get("name", r.get("Name", ""))
            dur = r.get("duration_minutes", r.get("DurationMinutes", 0))
            category_minutes[cat] = category_minutes.get(cat, 0) + dur
            app_minutes[name.lower()] = app_minutes.get(name.lower(), 0) + dur

        results = []
        for goal in self._goals:
            # 先按分类查找，再按应用名查找
            actual = category_minutes.get(goal.target, 0)
            if actual == 0:
                actual = app_minutes.get(goal.target.lower(), 0)

            if goal.minutes > 0:
                rate = actual / goal.minutes * 100
            else:
                rate = 100.0 if actual == 0 else float('inf')

            if goal.goal_type == "min":
                achieved = actual >= goal.minutes
            else:  # max
                achieved = actual <= goal.minutes

            results.append({
                "goal": goal,
                "actual_minutes": actual,
                "achievement_rate": rate,
                "achieved": achieved,
            })
        return results

    def evaluate_weekly(self):
        """
        评估过去 7 天的达成趋势
        Returns: [{"goal": UsageGoal, "daily_achieved": [bool,...],
                   "achievement_days": int}]
        """
        today = datetime.now()
        dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

        results = []
        for goal in self._goals:
            daily_achieved = []
            for date in dates:
                day_results = self.evaluate(date)
                for r in day_results:
                    if r["goal"].target == goal.target:
                        daily_achieved.append(r["achieved"])
                        break
                else:
                    daily_achieved.append(False)

            results.append({
                "goal": goal,
                "daily_achieved": daily_achieved,
                "achievement_days": sum(daily_achieved),
            })
        return results
