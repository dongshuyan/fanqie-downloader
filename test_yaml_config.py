#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试YAML配置文件功能
"""

import sys
import os
sys.path.append('src')

from importlib import import_module
main_module = import_module('main')
Config = main_module.Config
NovelDownloader = main_module.NovelDownloader

def test_yaml_config():
    """测试YAML配置文件加载"""
    print("🔥 测试YAML配置文件功能")
    print("="*50)
    
    # 测试1: 加载默认配置
    print("\n📋 测试1: 默认配置")
    default_config = Config()
    print(f"  启用TXT: {default_config.enable_txt}")
    print(f"  启用JSON: {default_config.enable_json}")
    print(f"  线程数: {default_config.thread_count}")
    print(f"  延时模式: {default_config.delay_mode}")
    print(f"  延时范围: {default_config.delay}")
    
    # 测试2: 从YAML文件加载配置
    print("\n📋 测试2: 从YAML文件加载配置")
    if os.path.exists('config.yaml'):
        yaml_config = Config.from_yaml('config.yaml')
        print(f"  启用TXT: {yaml_config.enable_txt}")
        print(f"  启用JSON: {yaml_config.enable_json}")
        print(f"  启用EPUB: {yaml_config.enable_epub}")
        print(f"  线程数: {yaml_config.thread_count}")
        print(f"  延时模式: {yaml_config.delay_mode}")
        print(f"  延时范围: {yaml_config.delay}")
        print(f"  TXT目录: {yaml_config.txt_download_dir}")
        print(f"  JSON目录: {yaml_config.json_backup_dir}")
        print(f"  删除章节文件夹: {yaml_config.delete_chapters_after_merge}")
    else:
        print("  ⚠️ config.yaml 不存在")
        
    # 测试3: 创建下载器实例
    print("\n📋 测试3: 创建下载器实例")
    try:
        test_config = Config()
        downloader = NovelDownloader(test_config)
        print(f"  ✅ 下载器创建成功")
        print(f"  📁 TXT目录: {downloader.novel_downloads_dir}")
        print(f"  📁 JSON目录: {downloader.bookstore_dir}")
        
        # 检查目录是否正确创建
        dirs_exist = []
        if test_config.enable_txt and os.path.exists(downloader.novel_downloads_dir):
            dirs_exist.append("TXT")
        if test_config.enable_json and os.path.exists(downloader.bookstore_dir):
            dirs_exist.append("JSON")
            
        print(f"  ✅ 已创建目录: {', '.join(dirs_exist) if dirs_exist else '无'}")
        
    except Exception as e:
        print(f"  ❌ 下载器创建失败: {e}")
    
    print("\n🎉 配置文件测试完成！")

if __name__ == "__main__":
    test_yaml_config() 