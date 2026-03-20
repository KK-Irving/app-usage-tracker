# -*- coding: utf-8 -*-
import psutil
import time
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# First call returns 0, need interval
cpu = psutil.cpu_percent(interval=1)
print(f"CPU 使用率: {cpu}%")

# Per CPU
per_cpu = psutil.cpu_percent(interval=1, percpu=True)
print(f"各核心: {per_cpu}")

# CPU times
times = psutil.cpu_times()
print(f"CPU Time - User: {times.user:.1f}s, System: {times.system:.1f}s")
