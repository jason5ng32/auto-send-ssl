#!/usr/bin/env python3
"""
证书刷新模块
使用 certbot 强制更新证书
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from logger_config import setup_logger

logger = setup_logger(__name__, os.getenv('LOG_LEVEL', 'INFO'))


def refresh_certificate(domain: str, max_retries: int = 3, retry_delay: int = 5) -> bool:
    """
    使用 certbot 强制更新证书
    
    Args:
        domain: 域名
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
        
    Returns:
        bool: 是否成功更新
    """
    logger.info(f"开始刷新域名证书: {domain}")
    
    # certbot 命令
    cmd = [
        'certbot', 'renew',
        '--force-renewal',
        '--cert-name', domain,
        '--non-interactive'
    ]
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"尝试更新证书 (第 {attempt}/{max_retries} 次)")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                logger.info("证书更新成功")
                logger.debug(f"输出: {result.stdout}")
                return True
            else:
                logger.error(f"证书更新失败 (返回码: {result.returncode})")
                logger.error(f"错误输出: {result.stderr}")
                
                if attempt < max_retries:
                    logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                    
        except subprocess.TimeoutExpired:
            logger.error("证书更新超时")
            if attempt < max_retries:
                logger.info(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
                
        except FileNotFoundError:
            logger.error("未找到 certbot 命令，请确保已安装 certbot")
            return False
            
        except Exception as e:
            logger.error(f"更新证书时发生错误: {e}")
            if attempt < max_retries:
                logger.info(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
    
    logger.error(f"证书更新失败，已重试 {max_retries} 次")
    return False


def wait_for_cert_ready(cert_path: str, timeout: int = 60) -> bool:
    """
    等待证书文件生成完成
    
    Args:
        cert_path: 证书目录路径
        timeout: 超时时间（秒）
        
    Returns:
        bool: 证书是否准备就绪
    """
    required_files = ['privkey.pem', 'fullchain.pem']
    cert_dir = Path(cert_path)
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        all_exist = all((cert_dir / f).exists() for f in required_files)
        
        if all_exist:
            logger.info("所有证书文件已生成")
            return True
        
        logger.debug(f"等待证书文件生成... ({int(time.time() - start_time)}s)")
        time.sleep(2)
    
    logger.error(f"等待证书文件超时 ({timeout}s)")
    return False


def refresh_and_wait(domain: str, cert_path: str) -> bool:
    """
    刷新证书并等待完成
    
    Args:
        domain: 域名
        cert_path: 证书路径
        
    Returns:
        bool: 是否成功
    """
    # 刷新证书
    if not refresh_certificate(domain):
        return False
    
    # 等待证书文件就绪
    if not wait_for_cert_ready(cert_path):
        return False
    
    logger.info("证书刷新并验证完成")
    return True


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    
    domain = os.getenv('CERT_DOMAIN', 'example.com')
    cert_path = os.getenv('CERT_PATH', f'/etc/letsencrypt/live/{domain}')
    
    logger.info(f"刷新证书: {domain}")
    logger.info(f"证书路径: {cert_path}")
    
    success = refresh_and_wait(domain, cert_path)
    
    if success:
        print("✓ 证书刷新成功")
        sys.exit(0)
    else:
        print("✗ 证书刷新失败")
        sys.exit(1)
