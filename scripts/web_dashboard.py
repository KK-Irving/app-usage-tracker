# -*- coding: utf-8 -*-
"""
Web 仪表盘 (WebDashboard)
使用 Flask 提供本地 HTTP 服务，展示使用数据和交互式图表
"""
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

ROOT_DIR = Path(__file__).parent.parent
TEMPLATE_DIR = ROOT_DIR / "templates"

try:
    from flask import Flask, jsonify, request, render_template
    _flask_available = True
except ImportError:
    _flask_available = False


def create_app(data_store):
    """创建并配置 Flask 应用"""
    if not _flask_available:
        print("❌ Flask 未安装。安装: pip install flask")
        return None

    app = Flask(__name__, template_folder=str(TEMPLATE_DIR))
    app.config["JSON_AS_ASCII"] = False

    @app.route("/")
    def index():
        return render_template("dashboard.html")

    @app.route("/goals")
    def goals_page():
        return render_template("goals.html")

    @app.route("/api/usage/today")
    def api_usage_today():
        today = datetime.now().strftime("%Y-%m-%d")
        records = data_store.get_usage_records(today)
        return _build_usage_summary(records)

    @app.route("/api/usage")
    def api_usage():
        start = request.args.get("start", datetime.now().strftime("%Y-%m-%d"))
        end = request.args.get("end", start)
        category = request.args.get("category")
        records = data_store.get_usage_records_range(start, end)
        if category:
            records = [r for r in records if r.get("category", r.get("Category", "")) == category]
        return jsonify({"records": records, "total": len(records)})

    @app.route("/api/usage/categories")
    def api_categories():
        date = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
        records = data_store.get_usage_records(date)
        cat_stats = defaultdict(float)
        for r in records:
            cat = r.get("category", r.get("Category", "其他"))
            cat_stats[cat] += r.get("duration_minutes", r.get("DurationMinutes", 0))
        total = sum(cat_stats.values())
        categories = [
            {"name": c, "minutes": m, "pct": round(m / total * 100, 1) if total > 0 else 0}
            for c, m in sorted(cat_stats.items(), key=lambda x: x[1], reverse=True)
        ]
        return jsonify({"categories": categories, "total_minutes": total})

    @app.route("/api/goals")
    def api_goals():
        try:
            from scripts.goal_manager import GoalManager
            gm = GoalManager(data_store)
            results = gm.evaluate()
            goals = []
            for r in results:
                goals.append({
                    "target": r["goal"].target,
                    "type": r["goal"].goal_type,
                    "target_minutes": r["goal"].minutes,
                    "actual_minutes": r["actual_minutes"],
                    "rate": round(r["achievement_rate"], 1),
                    "achieved": r["achieved"],
                })
            return jsonify({"goals": goals})
        except Exception as e:
            return jsonify({"goals": [], "error": str(e)})

    @app.route("/api/switches")
    def api_switches():
        date = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
        try:
            from scripts.switch_analyzer import SwitchAnalyzer
            sa = SwitchAnalyzer(data_store)
            hourly = sa.get_hourly_switch_counts(date)
            top_pairs = sa.get_top_switch_pairs(date)
            cost = sa.get_context_switch_cost(date)
            return jsonify({
                "hourly": hourly,
                "top_pairs": [{"from": f, "to": t, "count": c} for f, t, c in top_pairs],
                "cost_minutes": cost,
            })
        except Exception as e:
            return jsonify({"hourly": {}, "top_pairs": [], "cost_minutes": 0, "error": str(e)})

    @app.route("/api/projects")
    def api_projects():
        date = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
        try:
            from scripts.project_tracker import ProjectTracker
            pt = ProjectTracker(data_store)
            report = pt.get_project_report(date)
            return jsonify({"projects": report})
        except Exception as e:
            return jsonify({"projects": [], "error": str(e)})

    return app


def _build_usage_summary(records):
    """构建使用概览 JSON"""
    if not records:
        return jsonify({"total_minutes": 0, "categories": [], "top_apps": []})

    cat_stats = defaultdict(float)
    app_stats = defaultdict(lambda: {"minutes": 0, "category": ""})
    for r in records:
        cat = r.get("category", r.get("Category", "其他"))
        name = r.get("name", r.get("Name", ""))
        dur = r.get("duration_minutes", r.get("DurationMinutes", 0))
        cat_stats[cat] += dur
        app_stats[name]["minutes"] += dur
        app_stats[name]["category"] = cat

    total = sum(cat_stats.values())
    categories = [
        {"name": c, "minutes": round(m, 1), "pct": round(m / total * 100, 1) if total > 0 else 0}
        for c, m in sorted(cat_stats.items(), key=lambda x: x[1], reverse=True)
    ]
    top_apps = [
        {"name": n, "minutes": round(s["minutes"], 1), "category": s["category"]}
        for n, s in sorted(app_stats.items(), key=lambda x: x[1]["minutes"], reverse=True)[:5]
    ]
    return jsonify({"total_minutes": round(total, 1), "categories": categories, "top_apps": top_apps})


def run_dashboard(data_store, host="127.0.0.1", port=8080):
    """启动 Web 仪表盘"""
    app = create_app(data_store)
    if app:
        print(f"🌐 Web 仪表盘启动: http://{host}:{port}")
        app.run(host=host, port=port, debug=False)
