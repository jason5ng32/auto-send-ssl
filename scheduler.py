#!/usr/bin/env python3
"""
调度器模块
支持将程序作为守护进程运行，定期执行证书检查和发送任务
"""

import os
import re
import time
import signal
import sys
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from logger_config import setup_logger

logger = setup_logger(__name__, os.getenv('LOG_LEVEL', 'INFO'))


def parse_interval(interval_str: str) -> dict:
    """
    解析时间间隔字符串
    
    支持格式：
    - "1d" 或 "1" - 1天
    - "12h" - 12小时
    - "3600s" - 3600秒
    
    Args:
        interval_str: 时间间隔字符串
        
    Returns:
        dict: 包含时间单位和值的字典，用于 IntervalTrigger
    """
    # 匹配数字和可选的单位
    match = re.match(r'^(\d+)([dhsm]?)$', interval_str.strip().lower())
    
    if not match:
        raise ValueError(f"无效的时间间隔格式: {interval_str}，应为如: 1d, 12h, 3600s")
    
    value = int(match.group(1))
    unit = match.group(2) or 'd'  # 默认为天
    
    # 转换为 APScheduler 支持的单位
    unit_map = {
        'd': 'days',
        'h': 'hours',
        's': 'seconds',
        'm': 'minutes'
    }
    
    if unit not in unit_map:
        raise ValueError(f"不支持的时间单位: {unit}，支持: d(天), h(小时), s(秒), m(分钟)")
    
    return {unit_map[unit]: value}


def create_scheduler(job_func, interval_str: str = '1d') -> BlockingScheduler:
    """
    创建调度器
    
    Args:
        job_func: 要执行的任务函数
        interval_str: 时间间隔字符串
        
    Returns:
        BlockingScheduler: 配置好的调度器
    """
    scheduler = BlockingScheduler()
    
    # 解析时间间隔
    interval_kwargs = parse_interval(interval_str)
    
    # 添加定时任务
    scheduler.add_job(
        job_func,
        trigger=IntervalTrigger(**interval_kwargs),
        id='cert_check_job',
        name='SSL证书检查和发送',
        replace_existing=True
    )
    
    logger.info(f"调度器已配置，执行间隔: {interval_str} ({interval_kwargs})")
    
    return scheduler


def run_daemon(job_func, interval_str: str = '1d'):
    """
    以守护进程模式运行
    
    Args:
        job_func: 要执行的任务函数
        interval_str: 时间间隔字符串
    """
    logger.info("=" * 60)
    logger.info("SSL证书自动发送守护进程启动")
    logger.info("=" * 60)
    logger.info(f"执行间隔: {interval_str}")
    logger.info(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 创建调度器
    scheduler = create_scheduler(job_func, interval_str)
    
    # 注册信号处理
    def signal_handler(signum, frame):
        logger.info(f"\n接收到信号 {signum}，正在关闭调度器...")
        scheduler.shutdown()
        logger.info("调度器已关闭")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 立即执行一次
    logger.info("\n立即执行初始任务...")
    try:
        job_func()
    except Exception as e:
        logger.error(f"初始任务执行失败: {e}", exc_info=True)
    
    # 启动调度器
    logger.info(f"\n调度器已启动，下次执行时间将基于间隔 {interval_str}")
    logger.info("按 Ctrl+C 停止程序\n")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("程序正常退出")


if __name__ == '__main__':
    # 测试代码
    def test_job():
        print(f"[{datetime.now()}] 测试任务执行")
    
    # 测试解析
    test_cases = ['1d', '12h', '3600s', '30m', '1']
    for case in test_cases:
        result = parse_interval(case)
        print(f"{case} -> {result}")
    
    # 测试运行（10秒间隔）
    # run_daemon(test_job, '10s')
