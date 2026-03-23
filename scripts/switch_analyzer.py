# -*- coding: utf-8 -*-
"""
应用切换频率分析 (SwitchAnalyzer)
统计每小时切换次数、高频时段、上下文切换成本、Top 切换对
"""
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class SwitchAnalyzer:
    DEFAULT_RECOVERY_MINUTES = 2.0  # 默认切换恢复时间（分钟）

    def __init__(self, data_store):
        self.data_store = data_store

    def get_hourly_switch_counts(self, date):
        """获取每小时切换次数 {hour: count}"""
        switches = self.data_store.get_context_switches(date)
        counts = defaultdict(int)
        for s in switches:
            ts = s.get("timestamp", "")
            try:
                hour = int(ts[11:13]) if len(ts) >= 13 else 0
            except (ValueError, IndexError):
                hour = 0
            counts[hour] += 1
        return dict(counts)

    def get_high_frequency_hours(self, date):
        """获取切换频率异常高的时段（> 平均值 × 1.5）"""
        counts = self.get_hourly_switch_counts(date)
        if not counts:
            return []
        values = list(counts.values())
        avg = sum(values) / len(values)
        threshold = avg * 1.5
        return sorted([h for h, c in counts.items() if c > threshold])

    def get_context_switch_cost(self, date):
        """计算上下文切换成本（分钟）= 总切换次数 × DEFAULT_RECOVERY_MINUTES"""
        switches = self.data_store.get_context_switches(date)
        return len(switches) * self.DEFAULT_RECOVERY_MINUTES

    def get_top_switch_pairs(self, date, top_n=5):
        """
        获取最频繁的切换对
        Returns: [(from_app, to_app, count), ...]
        """
        switches = self.data_store.get_context_switches(date)
        pair_counts = Counter()
        for s in switches:
            pair = (s.get("from_app", ""), s.get("to_app", ""))
            pair_counts[pair] += 1
        return [(f, t, c) for (f, t), c in pair_counts.most_common(top_n)]

    def get_switch_focus_correlation(self, date):
        """
        计算切换频率与专注度的相关性
        Returns: {"hourly_data": [...], "correlation": float}
        """
        hourly_switches = self.get_hourly_switch_counts(date)
        focus_sessions = self.data_store.get_focus_sessions(date)

        # 按小时汇总专注分钟数
        hourly_focus = defaultdict(float)
        for fs in focus_sessions:
            ts = fs.get("timestamp", "")
            try:
                hour = int(ts[11:13]) if len(ts) >= 13 else 0
            except (ValueError, IndexError):
                hour = 0
            hourly_focus[hour] += fs.get("duration_minutes", 0)

        # 构建小时数据
        all_hours = set(hourly_switches.keys()) | set(hourly_focus.keys())
        hourly_data = []
        for h in sorted(all_hours):
            hourly_data.append({
                "hour": h,
                "switches": hourly_switches.get(h, 0),
                "focus_score": hourly_focus.get(h, 0),
            })

        # 计算皮尔逊相关系数
        correlation = self._pearson_correlation(
            [d["switches"] for d in hourly_data],
            [d["focus_score"] for d in hourly_data],
        )

        return {"hourly_data": hourly_data, "correlation": correlation}

    @staticmethod
    def _pearson_correlation(x, y):
        """计算皮尔逊相关系数，数据不足时返回 0"""
        n = len(x)
        if n < 2:
            return 0.0
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        std_x = (sum((xi - mean_x) ** 2 for xi in x)) ** 0.5
        std_y = (sum((yi - mean_y) ** 2 for yi in y)) ** 0.5
        if std_x == 0 or std_y == 0:
            return 0.0
        r = cov / (std_x * std_y)
        # 确保在 [-1, 1] 范围内（浮点精度）
        return max(-1.0, min(1.0, r))
