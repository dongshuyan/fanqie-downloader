#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动测试脚本 - 验证main-fix.py的TXT文件生成功能
"""

import sys
import os
sys.path.append('src')

from importlib import import_module
main_fix = import_module('main-fix')
NovelDownloader = main_fix.NovelDownloader
Config = main_fix.Config
SaveMode = main_fix.SaveMode

def test_download():
    """测试下载功能"""
    print("🔥 开始自动测试main-fix.py")
    print("📋 目标小说ID: 7520128677003136024")
    print("-"*50)
    
    # 配置下载器
    config = Config()
    config.save_mode = SaveMode.SINGLE_TXT  # 确保生成TXT
    config.save_path = os.getcwd()  # 保存到当前目录
    
    # 创建下载器
    downloader = NovelDownloader(config)
    
    # 开始下载
    novel_id = 7520128677003136024
    result = downloader.download_novel(novel_id)
    
    print(f"\n📊 下载结果: {result}")
    
    # 检查生成的文件
    txt_files = [f for f in os.listdir('.') if f.endswith('.txt') and '想和你互相耽误' in f]
    json_files = [f for f in os.listdir('src/data/bookstore') if f.endswith('.json') and '想和你互相耽误' in f]
    
    print(f"\n📁 文件检查:")
    print(f"✅ TXT文件: {txt_files}")
    print(f"✅ JSON文件: {json_files}")
    
    if txt_files:
        txt_file = txt_files[0]
        file_size = os.path.getsize(txt_file)
        print(f"📄 TXT文件大小: {file_size} 字节")
        
        # 读取前200个字符
        with open(txt_file, 'r', encoding='UTF-8') as f:
            preview = f.read(200)
            print(f"📖 内容预览:\n{preview}...")
    
    print("\n🎉 测试完成！")

if __name__ == "__main__":
    test_download() 