# -*- coding: utf-8 -*-
"""
统一应用分类引擎
所有模块通过此模块获取分类结果
"""
import json
from pathlib import Path

# 分类优先级（从高到低）
CATEGORY_PRIORITY = ["开发", "工作", "社交", "娱乐", "系统", "其他"]

# 默认分类配置
DEFAULT_CATEGORIES = {
    "开发": {
        "color": "🟣",
        "apps": ["python", "java", "node", "npm", "git", "docker", "idea64", "pycharm", "webstorm", "sublime", "gitkraken"]
    },
    "工作": {
        "color": "🔵",
        "apps": ["chrome", "msedge", "firefox", "vscode", "code", "notepad++", "powershell", "cmd", "DingTalk", "钉钉", "企业微信", "飞书", "outlook", "teams", "slack", "zoom"]
    },
    "社交": {
        "color": "🟡",
        "apps": ["微信", "WeChat", "QQ", "Telegram", "Discord", "WhatsApp"]
    },
    "娱乐": {
        "color": "🔴",
        "apps": ["Spotify", "网易云音乐", "vlc", "Steam", "epic", "bilibili", "PotPlayer"]
    },
    "系统": {
        "color": "⚪",
        "apps": ["explorer", "System", "svchost", "RuntimeBroker", "csrss", "services"]
    }
}

CONFIG_FILE = Path(__file__).parent / "config" / "app_categories.json"


def load_categories():
    """加载分类配置"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print("⚠️ 分类配置文件格式错误，使用默认配置")
    return DEFAULT_CATEGORIES.copy()


def save_categories(categories):
    """保存分类配置到 JSON 文件"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)


def classify_app(app_name):
    """
    统一分类接口，按优先级遍历分类
    Args:
        app_name: 进程名称
    Returns:
        (分类名称, 颜色图标)
    """
    categories = load_categories()
    app_lower = app_name.lower()

    for priority_cat in CATEGORY_PRIORITY:
        if priority_cat == "其他":
            continue
        if priority_cat in categories:
            info = categories[priority_cat]
            for pattern in info.get("apps", []):
                if pattern.lower() in app_lower:
                    return priority_cat, info.get("color", "⚪")

    return "其他", "⚪"


def add_app_to_category(category, app_name):
    """添加应用到指定分类并持久化"""
    categories = load_categories()
    if category not in categories:
        categories[category] = {"color": "⚪", "apps": []}
    apps = categories[category].get("apps", [])
    if app_name not in apps:
        apps.append(app_name)
        categories[category]["apps"] = apps
        save_categories(categories)
        return True
    return False


def remove_app_from_category(category, app_name):
    """从指定分类移除应用并持久化"""
    categories = load_categories()
    if category in categories:
        apps = categories[category].get("apps", [])
        if app_name in apps:
            apps.remove(app_name)
            categories[category]["apps"] = apps
            save_categories(categories)
            return True
    return False


def get_all_categories():
    """获取所有分类"""
    return load_categories()
