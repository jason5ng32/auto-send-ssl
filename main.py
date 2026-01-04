#!/usr/bin/env python3
"""
SSL证书自动发送主程序
协调整个证书检查、更新、打包和发送流程
"""

import os
import sys
import importlib.util
from pathlib import Path
from dotenv import load_dotenv
from logger_config import setup_logger

# 动态导入带连字符的模块
def import_module_from_file(module_name, file_path):
    """动态导入Python模块"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# 获取当前目录
current_dir = Path(__file__).parent

# 导入自定义模块
get_files = import_module_from_file('get_files', current_dir / 'get-files.py')
refresh_certs = import_module_from_file('refresh_certs', current_dir / 'refresh-certs.py')
zip_files = import_module_from_file('zip_files', current_dir / 'zip-files.py')
sendmain = import_module_from_file('sendmain', current_dir / 'sendmain.py')

# 导入需要的函数
validate_certificates = get_files.validate_certificates
refresh_and_wait = refresh_certs.refresh_and_wait
create_and_verify = zip_files.create_and_verify
send_with_retry = sendmain.send_with_retry

# 配置日志
logger = setup_logger(__name__, os.getenv('LOG_LEVEL', 'INFO'))


def run_check():
    """
    执行一次完整的证书检查和发送流程
    """
    logger.info("=" * 60)
    logger.info("SSL证书自动发送程序启动")
    logger.info("=" * 60)
    
    # 获取配置（.env已在main函数中加载）
    domain = os.getenv('CERT_DOMAIN')
    cert_path = os.getenv('CERT_PATH')
    threshold_days = int(os.getenv('CERT_AGE_THRESHOLD', '30'))
    api_key = os.getenv('RESEND_API_KEY')
    from_email = os.getenv('FROM_EMAIL')
    to_email = os.getenv('TO_EMAIL')
    sender_name = os.getenv('SENDER_NAME')  # 可选配置
    
    # 验证必需的环境变量
    required_vars = {
        'CERT_DOMAIN': domain,
        'CERT_PATH': cert_path,
        'RESEND_API_KEY': api_key,
        'FROM_EMAIL': from_email,
        'TO_EMAIL': to_email
    }
    
    missing_vars = [k for k, v in required_vars.items() if not v]
    if missing_vars:
        logger.error(f"缺少必需的环境变量: {', '.join(missing_vars)}")
        logger.error("请检查 .env 文件配置")
        return 1
    
    logger.info(f"域名: {domain}")
    logger.info(f"证书路径: {cert_path}")
    logger.info(f"证书阈值: {threshold_days} 天")
    
    # 步骤1: 检查证书
    logger.info("\n" + "-" * 60)
    logger.info("步骤 1/4: 检查证书状态")
    logger.info("-" * 60)
    
    cert_status = validate_certificates(cert_path, threshold_days)
    
    if cert_status['needs_refresh']:
        logger.warning("证书需要刷新")
        
        # 步骤2: 刷新证书
        logger.info("\n" + "-" * 60)
        logger.info("步骤 2/4: 刷新证书")
        logger.info("-" * 60)
        
        if not refresh_and_wait(domain, cert_path):
            logger.error("证书刷新失败")
            return 1
        
        logger.info("证书刷新成功")
    else:
        logger.info("证书状态良好，无需刷新")
        logger.info("\n" + "-" * 60)
        logger.info("步骤 2/4: 刷新证书 (已跳过)")
        logger.info("-" * 60)
    
    # 步骤3: 打包证书
    logger.info("\n" + "-" * 60)
    logger.info("步骤 3/4: 打包证书文件")
    logger.info("-" * 60)
    
    try:
        zip_path = create_and_verify(cert_path, domain=domain)
        logger.info(f"证书打包成功: {zip_path}")
    except Exception as e:
        logger.error(f"证书打包失败: {e}")
        return 1
    
    # 步骤4: 发送邮件
    logger.info("\n" + "-" * 60)
    logger.info("步骤 4/4: 发送邮件")
    logger.info("-" * 60)
    
    if not send_with_retry(zip_path, from_email, to_email, domain, api_key, sender_name=sender_name):
        logger.error("邮件发送失败")
        return 1
    
    logger.info("邮件发送成功")
    
    # 清理 zip 文件（可选）
    cleanup = os.getenv('CLEANUP_ZIP', 'false').lower() == 'true'
    if cleanup:
        try:
            Path(zip_path).unlink()
            logger.info(f"已清理 zip 文件: {zip_path}")
        except Exception as e:
            logger.warning(f"清理 zip 文件失败: {e}")
    
    # 完成
    logger.info("\n" + "=" * 60)
    logger.info("所有步骤完成！")
    logger.info("=" * 60)
    
    return 0


def main():
    """
    主入口函数，支持一次性执行和守护模式
    """
    # 首先加载环境变量（必须在最开始）
    load_dotenv()
    
    # 检查是否启用守护模式
    daemon_mode = os.getenv('DAEMON_MODE', 'false').lower() == 'true'
    
    if daemon_mode:
        # 守护模式：定期执行
        from scheduler import run_daemon
        
        schedule_interval = os.getenv('SCHEDULE_INTERVAL', '1d')
        logger.info(f"守护模式已启用，调度间隔: {schedule_interval}")
        
        try:
            run_daemon(run_check, schedule_interval)
        except Exception as e:
            logger.error(f"守护进程运行失败: {e}", exc_info=True)
            return 1
    else:
        # 一次性执行模式
        try:
            return run_check()
        except KeyboardInterrupt:
            logger.warning("\n程序被用户中断")
            return 130
        except Exception as e:
            logger.exception(f"程序发生未处理的异常: {e}")
            return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.warning("\n程序被用户中断")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"程序发生未处理的异常: {e}")
        sys.exit(1)
