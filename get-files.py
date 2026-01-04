#!/usr/bin/env python3
"""
证书文件查找和验证模块
检查证书是否存在以及是否在指定天数内更新
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Tuple, Optional
from logger_config import setup_logger

logger = setup_logger(__name__, os.getenv('LOG_LEVEL', 'INFO'))


def check_cert_exists(cert_path: str) -> bool:
    """
    检查证书文件是否存在
    
    Args:
        cert_path: 证书目录路径
        
    Returns:
        bool: 证书文件是否都存在
    """
    required_files = ['privkey.pem', 'fullchain.pem']
    cert_dir = Path(cert_path)
    
    if not cert_dir.exists():
        logger.warning(f"证书目录不存在: {cert_path}")
        return False
    
    for file_name in required_files:
        file_path = cert_dir / file_name
        if not file_path.exists():
            logger.warning(f"缺少证书文件: {file_path}")
            return False
    
    logger.info(f"所有证书文件存在于: {cert_path}")
    return True


def check_cert_age(cert_path: str, threshold_days: int = 30) -> Tuple[bool, Optional[int]]:
    """
    检查证书的有效期是否在指定天数内到期
    
    Args:
        cert_path: 证书目录路径
        threshold_days: 到期前多少天需要更新
        
    Returns:
        Tuple[bool, Optional[int]]: (证书是否新鲜不需更新, 距离到期的天数)
    """
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    
    cert_file = Path(cert_path) / 'fullchain.pem'
    
    if not cert_file.exists():
        logger.error(f"证书文件不存在: {cert_file}")
        return False, None
    
    try:
        # 读取证书文件
        with open(cert_file, 'rb') as f:
            cert_data = f.read()
        
        # 解析证书（读取第一个证书）
        cert = x509.load_pem_x509_certificate(cert_data, default_backend())
        
        # 获取证书的有效期
        not_before = cert.not_valid_before_utc
        not_after = cert.not_valid_after_utc
        
        # 计算距离到期的天数
        now = datetime.now(not_after.tzinfo)  # 使用证书的时区
        days_until_expiry = (not_after - now).days
        
        # 判断是否需要更新
        # 如果距离到期还有 threshold_days 天以上，则认为证书新鲜
        is_fresh = days_until_expiry > threshold_days
        
        if is_fresh:
            logger.info(f"证书有效期正常，还有 {days_until_expiry} 天到期 (阈值: {threshold_days} 天)")
            logger.debug(f"证书有效期: {not_before.strftime('%Y-%m-%d')} 至 {not_after.strftime('%Y-%m-%d')}")
        else:
            if days_until_expiry > 0:
                logger.warning(f"证书即将到期，还有 {days_until_expiry} 天 (阈值: {threshold_days} 天)")
            else:
                logger.error(f"证书已过期 {abs(days_until_expiry)} 天！")
        
        return is_fresh, days_until_expiry
        
    except Exception as e:
        logger.error(f"解析证书失败: {e}")
        return False, None


def get_cert_files(cert_path: str) -> list:
    """
    获取证书目录中的所有文件路径
    
    Args:
        cert_path: 证书目录路径
        
    Returns:
        list: 证书文件路径列表
    """
    required_files = ['privkey.pem', 'fullchain.pem']
    cert_dir = Path(cert_path)
    
    file_paths = []
    for file_name in required_files:
        file_path = cert_dir / file_name
        if file_path.exists():
            file_paths.append(str(file_path))
    
    return file_paths


def validate_certificates(cert_path: str, threshold_days: int = 30) -> dict:
    """
    综合验证证书状态
    
    Args:
        cert_path: 证书目录路径
        threshold_days: 时间阈值（天数）
        
    Returns:
        dict: 验证结果
    """
    result = {
        'exists': False,
        'is_fresh': False,
        'age_days': None,
        'files': [],
        'needs_refresh': True
    }
    
    # 检查文件是否存在
    result['exists'] = check_cert_exists(cert_path)
    
    if not result['exists']:
        logger.error("证书文件不完整，需要刷新")
        return result
    
    # 检查证书年龄
    is_fresh, age_days = check_cert_age(cert_path, threshold_days)
    result['is_fresh'] = is_fresh
    result['age_days'] = age_days
    
    # 获取文件列表
    result['files'] = get_cert_files(cert_path)
    
    # 判断是否需要刷新
    result['needs_refresh'] = not (result['exists'] and result['is_fresh'])
    
    return result


if __name__ == '__main__':
    # 测试代码
    from dotenv import load_dotenv
    load_dotenv()
    
    cert_path = os.getenv('CERT_PATH', './tmp/live/example.com')
    threshold = int(os.getenv('CERT_AGE_THRESHOLD', '30'))
    
    logger.info(f"检查证书: {cert_path}")
    result = validate_certificates(cert_path, threshold)
    
    print(f"\n证书验证结果:")
    print(f"  存在: {result['exists']}")
    print(f"  新鲜: {result['is_fresh']}")
    print(f"  年龄: {result['age_days']} 天")
    print(f"  需要刷新: {result['needs_refresh']}")
    print(f"  文件数量: {len(result['files'])}")
    
    sys.exit(0 if not result['needs_refresh'] else 1)
