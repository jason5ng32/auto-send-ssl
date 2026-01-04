#!/usr/bin/env python3
"""
日志配置模块
统一配置所有模块的日志输出到文件和控制台
"""

import os
import logging
from pathlib import Path
from datetime import datetime


def setup_logger(name: str, log_level: str = 'INFO') -> logging.Logger:
    """
    配置日志记录器
    
    Args:
        name: 日志记录器名称
        log_level: 日志级别
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 创建日志目录
    log_dir = Path('logs')
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成日志文件名（按日期）
    log_file = log_dir / f"ssl-auto-send_{datetime.now().strftime('%Y%m%d')}.log"
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
    file_handler.setFormatter(formatter)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


if __name__ == '__main__':
    # 测试日志配置
    logger = setup_logger('test', 'DEBUG')
    logger.debug('这是调试信息')
    logger.info('这是普通信息')
    logger.warning('这是警告信息')
    logger.error('这是错误信息')
    print(f"日志已保存到: logs/ssl-auto-send_{datetime.now().strftime('%Y%m%d')}.log")
