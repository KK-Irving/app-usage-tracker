# -*- coding: utf-8 -*-
"""
多设备数据同步 (SyncManager)
支持本地文件夹和 S3 同步，生成跨设备汇总报告
"""
import hashlib
import json
import os
import platform
import shutil
import sys
import uuid
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
CONFIG_DIR = ROOT_DIR / "config"


@dataclass
class DeviceProfile:
    device_id: str
    device_name: str
    os_info: str


class SyncManager:
    CONFIG_PATH = CONFIG_DIR / "sync_config.json"

    def __init__(self, data_store):
        self.data_store = data_store
        self._device = self._get_or_create_device()

    def _generate_device_id(self):
        """基于 uuid.getnode() 的 SHA256 哈希"""
        return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()[:16]

    def _get_or_create_device(self):
        """从 sync_config.json 加载或首次创建设备配置"""
        config = self._load_config()
        device_id = config.get("device_id")
        if not device_id:
            device_id = self._generate_device_id()
            config["device_id"] = device_id
            config.setdefault("device_name", platform.node())
            config.setdefault("os_info", platform.platform())
            config.setdefault("remote_path", "")
            config.setdefault("sync_interval_minutes", 60)
            self._save_config(config)
        return DeviceProfile(
            device_id=device_id,
            device_name=config.get("device_name", platform.node()),
            os_info=config.get("os_info", platform.platform()),
        )

    def _load_config(self):
        if self.CONFIG_PATH.exists():
            try:
                with open(self.CONFIG_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _save_config(self, config):
        self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    @property
    def device(self):
        return self._device

    def push(self):
        """上传本地数据到远程存储"""
        config = self._load_config()
        remote_path = config.get("remote_path", "")
        if not remote_path:
            print("❌ 未配置远程存储路径，请在 config/sync_config.json 中设置 remote_path")
            return

        if remote_path.startswith("s3://"):
            self._sync_to_s3("push", remote_path)
        else:
            self._sync_to_local_folder("push", remote_path)

    def pull(self):
        """下载所有设备数据到 data/sync_temp/{device_id}/"""
        config = self._load_config()
        remote_path = config.get("remote_path", "")
        if not remote_path:
            print("❌ 未配置远程存储路径")
            return

        if remote_path.startswith("s3://"):
            self._sync_to_s3("pull", remote_path)
        else:
            self._sync_to_local_folder("pull", remote_path)

    def generate_cross_device_report(self):
        """聚合所有设备数据，生成跨设备汇总报告"""
        sync_temp = DATA_DIR / "sync_temp"
        if not sync_temp.exists():
            print("❌ 未找到同步数据，请先执行 sync --pull")
            return ""

        device_stats = {}
        category_totals = defaultdict(float)

        for device_dir in sync_temp.iterdir():
            if not device_dir.is_dir():
                continue
            device_id = device_dir.name
            device_minutes = 0
            device_categories = defaultdict(float)

            for f in device_dir.glob("usage_*.json"):
                try:
                    with open(f, 'r', encoding='utf-8') as fh:
                        data = json.load(fh)
                    for r in data.get("records", []):
                        dur = r.get("DurationMinutes", r.get("duration_minutes", 0))
                        cat = r.get("Category", r.get("category", "其他"))
                        device_minutes += dur
                        device_categories[cat] += dur
                        category_totals[cat] += dur
                except (json.JSONDecodeError, IOError):
                    continue

            device_stats[device_id] = {
                "total_minutes": device_minutes,
                "categories": dict(device_categories),
            }

        # 生成报告
        report = []
        report.append("=" * 60)
        report.append("📊 跨设备汇总报告")
        report.append("=" * 60)

        for did, stats in device_stats.items():
            hrs = int(stats["total_minutes"] // 60)
            mins = int(stats["total_minutes"] % 60)
            report.append(f"\n设备 {did}: {hrs}h {mins}m")
            for cat, dur in sorted(stats["categories"].items(), key=lambda x: x[1], reverse=True):
                report.append(f"  {cat}: {int(dur//60)}h {int(dur%60)}m")

        report.append(f"\n合并分类统计:")
        for cat, dur in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
            report.append(f"  {cat}: {int(dur//60)}h {int(dur%60)}m")

        report_text = "\n".join(report)
        print(report_text)
        return report_text

    def _sync_to_local_folder(self, direction, remote_path):
        """本地文件夹同步"""
        remote = Path(remote_path)
        if not remote.exists():
            if direction == "push":
                try:
                    remote.mkdir(parents=True, exist_ok=True)
                except OSError:
                    print(f"❌ 远程路径不可访问: {remote_path}")
                    return
            else:
                print(f"❌ 远程路径不可访问: {remote_path}")
                return

        if direction == "push":
            device_remote = remote / self._device.device_id
            device_remote.mkdir(parents=True, exist_ok=True)
            pushed = 0
            skipped = 0
            for f in DATA_DIR.iterdir():
                if f.is_file() and f.suffix == ".json":
                    dest = device_remote / f.name
                    # 跳过未变更文件
                    if dest.exists() and dest.stat().st_mtime >= f.stat().st_mtime:
                        skipped += 1
                        continue
                    shutil.copy2(str(f), str(dest))
                    pushed += 1
            # 也同步 db 文件
            db_file = DATA_DIR / "usage_tracker.db"
            if db_file.exists():
                dest = device_remote / db_file.name
                if not dest.exists() or dest.stat().st_mtime < db_file.stat().st_mtime:
                    shutil.copy2(str(db_file), str(dest))
                    pushed += 1
            print(f"✅ 推送完成: {pushed} 个文件已上传, {skipped} 个文件跳过（未变更）")

        elif direction == "pull":
            sync_temp = DATA_DIR / "sync_temp"
            sync_temp.mkdir(parents=True, exist_ok=True)
            pulled = 0
            for device_dir in remote.iterdir():
                if device_dir.is_dir():
                    local_dir = sync_temp / device_dir.name
                    local_dir.mkdir(parents=True, exist_ok=True)
                    for f in device_dir.iterdir():
                        if f.is_file():
                            shutil.copy2(str(f), str(local_dir / f.name))
                            pulled += 1
            print(f"✅ 拉取完成: {pulled} 个文件已下载")

    def _sync_to_s3(self, direction, remote_path):
        """S3 同步"""
        try:
            import boto3
        except ImportError:
            print("❌ boto3 未安装。安装: pip install boto3")
            return

        # 解析 s3://bucket/prefix
        parts = remote_path.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""

        try:
            s3 = boto3.client("s3")
            if direction == "push":
                device_prefix = f"{prefix}/{self._device.device_id}" if prefix else self._device.device_id
                for f in DATA_DIR.iterdir():
                    if f.is_file() and f.suffix in (".json", ".db"):
                        key = f"{device_prefix}/{f.name}"
                        s3.upload_file(str(f), bucket, key)
                print("✅ S3 推送完成")
            elif direction == "pull":
                sync_temp = DATA_DIR / "sync_temp"
                sync_temp.mkdir(parents=True, exist_ok=True)
                paginator = s3.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                    for obj in page.get("Contents", []):
                        key = obj["Key"]
                        rel = key[len(prefix):].lstrip("/")
                        local_path = sync_temp / rel
                        local_path.parent.mkdir(parents=True, exist_ok=True)
                        s3.download_file(bucket, key, str(local_path))
                print("✅ S3 拉取完成")
        except Exception as e:
            print(f"❌ S3 操作失败: {e}")
