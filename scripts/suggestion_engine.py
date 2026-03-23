# -*- coding: utf-8 -*-
"""
智能建议引擎 (SuggestionEngine)
基于历史数据进行模式识别并生成个性化建议
"""
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app_categories import classify_app

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"

WORK_CATEGORIES = {"工作", "开发"}
LEISURE_CATEGORIES = {"社交", "娱乐"}


@dataclass
class Suggestion:
    type: str           # "warning" | "insight" | "recommendation"
    content: str
    confidence: int     # 0-100
    related_data: dict

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


class SuggestionEngine:
    CACHE_PATH = DATA_DIR / "suggestions_cache.json"
    MIN_DATA_DAYS = 3

    def __init__(self, data_store, goal_manager=None):
        self.data_store = data_store
        self.goal_manager = goal_manager

    def generate_suggestions(self):
        """生成个性化建议，分析过去 7 天数据"""
        # 尝试加载缓存
        cached = self._load_cache()
        if cached is not None:
            return cached

        today = datetime.now()
        dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

        # 收集每天数据
        weekly_data = []
        for date in dates:
            records = self.data_store.get_usage_records(date)
            if records:
                weekly_data.append({"date": date, "records": records})

        if len(weekly_data) < self.MIN_DATA_DAYS:
            return self.get_suggestions_or_fallback()

        suggestions = []
        suggestions.extend(self._detect_efficiency_patterns(weekly_data))
        suggestions.extend(self._detect_goal_streaks())
        suggestions.extend(self._detect_peak_hours(weekly_data))

        # 按置信度降序排列
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        self._save_cache(suggestions)
        return suggestions

    def _detect_efficiency_patterns(self, weekly_data):
        """识别每周各天的效率模式"""
        suggestions = []
        day_scores = []
        for day in weekly_data:
            total = 0
            work_total = 0
            for r in day["records"]:
                dur = r.get("duration_minutes", r.get("DurationMinutes", 0))
                cat = r.get("category", r.get("Category", "其他"))
                total += dur
                if cat in WORK_CATEGORIES:
                    work_total += dur
            ratio = work_total / total if total > 0 else 0
            day_scores.append({"date": day["date"], "ratio": ratio})

        if day_scores:
            best = max(day_scores, key=lambda d: d["ratio"])
            weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            dt = datetime.strptime(best["date"], "%Y-%m-%d")
            day_name = weekday_names[dt.weekday()]
            confidence = self._calculate_confidence(len(weekly_data), best["ratio"])
            suggestions.append(Suggestion(
                type="insight",
                content=f"过去一周中，{day_name}({best['date']})效率最高，工作/开发占比 {best['ratio']*100:.0f}%",
                confidence=confidence,
                related_data={"best_day": best["date"], "ratio": best["ratio"]},
            ))
        return suggestions

    def _detect_goal_streaks(self):
        """检测连续多天目标未达成"""
        suggestions = []
        if not self.goal_manager:
            return suggestions

        today = datetime.now()
        goals = self.goal_manager.list_goals()
        for goal in goals:
            streak = 0
            for i in range(7):
                date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
                results = self.goal_manager.evaluate(date)
                achieved = False
                for r in results:
                    if r["goal"].target == goal.target:
                        achieved = r["achieved"]
                        break
                if not achieved:
                    streak += 1
                else:
                    break

            if streak >= 3:
                confidence = self._calculate_confidence(streak, 0.8)
                suggestions.append(Suggestion(
                    type="warning",
                    content=f"连续 {streak} 天「{goal.target}」目标未达成，建议调整目标或工作习惯",
                    confidence=confidence,
                    related_data={"target": goal.target, "streak_days": streak},
                ))
        return suggestions

    def _detect_peak_hours(self, weekly_data):
        """识别高效/低效时段模式"""
        suggestions = []
        hourly_work = defaultdict(float)
        hourly_leisure = defaultdict(float)
        hourly_total = defaultdict(float)

        for day in weekly_data:
            for r in day["records"]:
                hour = r.get("hour", 0)
                dur = r.get("duration_minutes", r.get("DurationMinutes", 0))
                cat = r.get("category", r.get("Category", "其他"))
                hourly_total[hour] += dur
                if cat in WORK_CATEGORIES:
                    hourly_work[hour] += dur
                elif cat in LEISURE_CATEGORIES:
                    hourly_leisure[hour] += dur

        # 找高效时段
        if hourly_total:
            work_ratios = {h: hourly_work[h] / hourly_total[h] for h in hourly_total if hourly_total[h] > 0}
            if work_ratios:
                best_hour = max(work_ratios, key=work_ratios.get)
                confidence = self._calculate_confidence(len(weekly_data), work_ratios[best_hour])
                suggestions.append(Suggestion(
                    type="recommendation",
                    content=f"{best_hour}:00 时段效率最高（工作占比 {work_ratios[best_hour]*100:.0f}%），建议安排重要工作",
                    confidence=confidence,
                    related_data={"peak_hour": best_hour, "ratio": work_ratios[best_hour]},
                ))

            leisure_ratios = {h: hourly_leisure[h] / hourly_total[h] for h in hourly_total if hourly_total[h] > 0}
            if leisure_ratios:
                worst_hour = max(leisure_ratios, key=leisure_ratios.get)
                if leisure_ratios[worst_hour] > 0.3:
                    confidence = self._calculate_confidence(len(weekly_data), leisure_ratios[worst_hour])
                    suggestions.append(Suggestion(
                        type="recommendation",
                        content=f"{worst_hour}:00 时段社交/娱乐占比较高（{leisure_ratios[worst_hour]*100:.0f}%），建议安排休息或轻量任务",
                        confidence=confidence,
                        related_data={"low_hour": worst_hour, "ratio": leisure_ratios[worst_hour]},
                    ))
        return suggestions

    @staticmethod
    def _calculate_confidence(data_days, consistency):
        """计算置信度 = min(100, data_days * 10 + consistency * 50)"""
        return min(100, int(data_days * 10 + consistency * 50))

    def _load_cache(self):
        """加载缓存的建议（当日有效）"""
        if not self.CACHE_PATH.exists():
            return None
        try:
            with open(self.CACHE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get("date") == datetime.now().strftime("%Y-%m-%d"):
                return [Suggestion.from_dict(s) for s in data.get("suggestions", [])]
        except (json.JSONDecodeError, IOError, TypeError):
            pass
        return None

    def _save_cache(self, suggestions):
        """缓存建议到 suggestions_cache.json"""
        self.CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "suggestions": [s.to_dict() for s in suggestions],
        }
        with open(self.CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_suggestions_or_fallback(self):
        """获取建议，数据不足时回退到 V1 固定模板"""
        # 尝试生成
        today = datetime.now()
        dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
        data_days = sum(1 for d in dates if self.data_store.get_usage_records(d))

        if data_days >= self.MIN_DATA_DAYS:
            return self.generate_suggestions()

        # 回退到固定模板
        return [
            Suggestion(
                type="recommendation",
                content="💡 数据积累中，建议将在 3 天后更加精准",
                confidence=0,
                related_data={"data_days": data_days},
            ),
            Suggestion(
                type="recommendation",
                content="⏰ 建议每 25 分钟休息 5 分钟（番茄工作法）",
                confidence=0,
                related_data={},
            ),
            Suggestion(
                type="recommendation",
                content="🎯 建议设定每日使用目标，量化时间管理",
                confidence=0,
                related_data={},
            ),
        ]
