#!/usr/bin/env python3
"""
邮件发送模块
使用 Resend API 发送证书文件
"""

import os
import sys
from pathlib import Path
from typing import Optional
import resend
from logger_config import setup_logger

logger = setup_logger(__name__, os.getenv('LOG_LEVEL', 'INFO'))


def send_certificate_email(
    zip_path: str,
    from_email: str,
    to_email: str,
    domain: str,
    api_key: str,
    sender_name: str = None
) -> bool:
    """
    通过 Resend 发送证书邮件
    
    Args:
        zip_path: zip 文件路径
        from_email: 发件人邮箱
        to_email: 收件人邮箱（支持单个邮箱或逗号分隔的多个邮箱）
        domain: 域名
        api_key: Resend API 密钥
        sender_name: 发件人名称（可选）
        
    Returns:
        bool: 是否发送成功
    """
    zip_file = Path(zip_path)
    
    if not zip_file.exists():
        logger.error(f"Zip 文件不存在: {zip_path}")
        return False
    
    # 解析收件人邮箱列表（支持逗号分隔）
    if isinstance(to_email, str):
        to_email_list = [email.strip() for email in to_email.split(',') if email.strip()]
    else:
        to_email_list = to_email
    
    if not to_email_list:
        logger.error("收件人邮箱列表为空")
        return False
    
    # 检查是否为测试模式
    test_mode = os.getenv('TEST_MODE', 'false').lower() == 'true'
    
    if test_mode:
        logger.warning("⚠️  测试模式已启用，邮件不会实际发送")
    
    # 设置 Resend API 密钥
    resend.api_key = api_key
    
    # 读取文件内容
    try:
        with open(zip_file, 'rb') as f:
            file_content = f.read()
    except Exception as e:
        logger.error(f"读取文件失败: {e}")
        return False
    
    # 准备邮件内容
    subject = f"SSL证书自动更新 - {domain}"
    html_content = f"""
    <html>
    <body>
        <h2>SSL证书自动更新通知</h2>
        <p>老板，</p>
        <p>这是来自自动化系统的SSL证书更新通知。</p>
        <ul>
            <li><strong>域名：</strong>{domain}</li>
            <li><strong>文件名：</strong>{zip_file.name}</li>
            <li><strong>文件大小：</strong>{len(file_content)} 字节</li>
        </ul>
        <p>证书文件已打包在附件中，请及时查收并部署。</p>
        <hr>
        <p style="color: #666; font-size: 12px;">
            此邮件由自动化系统发送，请勿回复。
        </p>
    </body>
    </html>
    """
    
    text_content = f"""
    SSL证书自动更新通知
    
    老板，
    
    这是来自自动化系统的SSL证书更新通知。
    
    域名：{domain}
    文件名：{zip_file.name}
    文件大小：{len(file_content)} 字节
    
    证书文件已打包在附件中，请及时查收并部署。
    
    ---
    此邮件由自动化系统发送，请勿回复。
    """
    
    try:
        # 格式化发件人地址
        if sender_name:
            formatted_from = f"{sender_name} <{from_email}>"
        else:
            formatted_from = from_email
        
        # 日志输出
        recipients_str = ", ".join(to_email_list)
        logger.info(f"发送邮件: {formatted_from} -> {recipients_str}")
        
        # 测试模式：只打印信息，不实际发送
        if test_mode:
            logger.info("=" * 60)
            logger.info("📧 测试模式 - 邮件内容预览")
            logger.info("=" * 60)
            logger.info(f"主题: {subject}")
            logger.info(f"发件人: {formatted_from}")
            logger.info(f"收件人: {recipients_str}")
            logger.info(f"附件: {zip_file.name} ({len(file_content)} 字节)")
            logger.info("=" * 60)
            logger.info("✓ 测试模式：邮件未实际发送（模拟发送成功）")
            logger.info("=" * 60)
            return True
        
        params = {
            "from": formatted_from,
            "to": to_email_list,
            "subject": subject,
            "html": html_content,
            "text": text_content,
            "attachments": [{
                "filename": zip_file.name,
                "content": list(file_content)
            }]
        }
        
        response = resend.Emails.send(params)
        
        logger.info(f"邮件发送成功，ID: {response.get('id', 'N/A')}")
        return True
        
    except resend.exceptions.ResendError as e:
        logger.error(f"Resend API 错误: {e}")
        return False
    except Exception as e:
        logger.error(f"发送邮件时发生错误: {e}")
        return False


def send_with_retry(
    zip_path: str,
    from_email: str,
    to_email: str,
    domain: str,
    api_key: str,
    max_retries: int = 3,
    sender_name: str = None
) -> bool:
    """
    带重试机制的邮件发送
    
    Args:
        zip_path: zip 文件路径
        from_email: 发件人邮箱
        to_email: 收件人邮箱
        domain: 域名
        api_key: Resend API 密钥
        max_retries: 最大重试次数
        sender_name: 发件人名称（可选）
        
    Returns:
        bool: 是否发送成功
    """
    import time
    
    for attempt in range(1, max_retries + 1):
        logger.info(f"尝试发送邮件 (第 {attempt}/{max_retries} 次)")
        
        if send_certificate_email(zip_path, from_email, to_email, domain, api_key, sender_name):
            return True
        
        
        if attempt < max_retries:
            delay = attempt * 2  # 递增延迟
            logger.info(f"等待 {delay} 秒后重试...")
            time.sleep(delay)
    
    logger.error(f"邮件发送失败，已重试 {max_retries} 次")
    return False


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    
    # 从环境变量获取配置
    api_key = os.getenv('RESEND_API_KEY')
    from_email = os.getenv('FROM_EMAIL')
    to_email = os.getenv('TO_EMAIL')
    domain = os.getenv('CERT_DOMAIN', 'example.com')
    
    # 验证必需的环境变量
    if not api_key:
        logger.error("未设置 RESEND_API_KEY 环境变量")
        sys.exit(1)
    if not from_email:
        logger.error("未设置 FROM_EMAIL 环境变量")
        sys.exit(1)
    if not to_email:
        logger.error("未设置 TO_EMAIL 环境变量")
        sys.exit(1)
    
    # 获取 zip 文件路径（从命令行参数或查找最新的）
    if len(sys.argv) > 1:
        zip_path = sys.argv[1]
    else:
        # 查找当前目录下最新的 zip 文件
        import glob
        zip_files = glob.glob('ssl_cert_*.zip')
        if not zip_files:
            logger.error("未找到证书 zip 文件")
            sys.exit(1)
        zip_path = max(zip_files, key=os.path.getctime)
        logger.info(f"使用最新的 zip 文件: {zip_path}")
    
    # 发送邮件
    success = send_with_retry(zip_path, from_email, to_email, domain, api_key)
    
    if success:
        print(f"✓ 邮件发送成功")
        sys.exit(0)
    else:
        print(f"✗ 邮件发送失败")
        sys.exit(1)
