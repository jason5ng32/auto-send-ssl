#!/usr/bin/env python3
"""
证书文件打包模块
将证书文件打包成 zip 格式
"""

import os
import sys
import zipfile
from pathlib import Path
from datetime import datetime
from logger_config import setup_logger

logger = setup_logger(__name__, os.getenv('LOG_LEVEL', 'INFO'))


def create_zip_archive(cert_path: str, output_path: str = None, domain: str = None) -> str:
    """
    创建证书文件的 zip 压缩包
    
    Args:
        cert_path: 证书目录路径
        output_path: 输出文件路径（可选）
        domain: 域名（用于命名，可选）
        
    Returns:
        str: 生成的 zip 文件路径
    """
    cert_dir = Path(cert_path)
    
    if not cert_dir.exists():
        raise FileNotFoundError(f"证书目录不存在: {cert_path}")
    
    # 确定输出文件名
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        domain_name = domain or cert_dir.name
        filename = f"ssl_cert_{domain_name}_{timestamp}.zip"
        
        # 使用 TMP_PATH 环境变量（如果设置）
        tmp_path = os.getenv('TMP_PATH')
        if tmp_path:
            output_path = str(Path(tmp_path) / filename)
        else:
            output_path = filename
    
    output_file = Path(output_path)
    
    # 确保输出目录存在
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 证书文件列表（只需要私钥和完整证书链）
    required_files = ['privkey.pem', 'fullchain.pem']
    
    logger.info(f"开始打包证书文件到: {output_file}")
    
    try:
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            files_added = 0
            
            for file_name in required_files:
                file_path = cert_dir / file_name
                
                if file_path.exists():
                    # 添加文件到 zip，使用相对路径作为存档名称
                    arcname = file_name
                    zipf.write(file_path, arcname=arcname)
                    files_added += 1
                    logger.debug(f"已添加: {file_name}")
                else:
                    logger.warning(f"文件不存在，跳过: {file_name}")
            
            if files_added == 0:
                raise ValueError("没有找到任何证书文件")
            
            logger.info(f"成功打包 {files_added} 个文件")
    
    except Exception as e:
        logger.error(f"打包过程中发生错误: {e}")
        # 如果创建失败，删除不完整的文件
        if output_file.exists():
            output_file.unlink()
        raise
    
    # 验证 zip 文件
    if not output_file.exists():
        raise FileNotFoundError("Zip 文件创建失败")
    
    file_size = output_file.stat().st_size
    logger.info(f"Zip 文件大小: {file_size} 字节")
    
    return str(output_file.absolute())


def verify_zip_archive(zip_path: str) -> bool:
    """
    验证 zip 文件的完整性
    
    Args:
        zip_path: zip 文件路径
        
    Returns:
        bool: 文件是否有效
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            # 测试 zip 文件完整性
            ret = zipf.testzip()
            if ret is not None:
                logger.error(f"Zip 文件损坏: {ret}")
                return False
            
            # 列出文件
            file_list = zipf.namelist()
            logger.info(f"Zip 包含 {len(file_list)} 个文件: {', '.join(file_list)}")
            
            return True
            
    except zipfile.BadZipFile:
        logger.error("无效的 zip 文件")
        return False
    except Exception as e:
        logger.error(f"验证 zip 文件时发生错误: {e}")
        return False


def create_and_verify(cert_path: str, output_path: str = None, domain: str = None) -> str:
    """
    创建并验证 zip 文件
    
    Args:
        cert_path: 证书目录路径
        output_path: 输出文件路径（可选）
        domain: 域名（可选）
        
    Returns:
        str: 生成的 zip 文件路径
    """
    # 创建压缩包
    zip_path = create_zip_archive(cert_path, output_path, domain)
    
    # 验证压缩包
    if not verify_zip_archive(zip_path):
        raise ValueError("Zip 文件验证失败")
    
    logger.info(f"证书打包完成: {zip_path}")
    return zip_path


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    
    cert_path = os.getenv('CERT_PATH', './tmp/live/example.com')
    domain = os.getenv('CERT_DOMAIN', 'example.com')
    
    try:
        zip_path = create_and_verify(cert_path, domain=domain)
        print(f"✓ 证书打包成功: {zip_path}")
        sys.exit(0)
    except Exception as e:
        print(f"✗ 证书打包失败: {e}")
        sys.exit(1)
