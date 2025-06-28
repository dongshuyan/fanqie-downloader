#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多格式下载功能
"""

import sys
import os
sys.path.append('src')

from importlib import import_module
main_module = import_module('main')
Config = main_module.Config
NovelDownloader = main_module.NovelDownloader

def test_multi_format_download():
    """测试多格式下载功能"""
    print("🚀 测试多格式下载功能")
    print("="*60)
    
    # 测试小说ID（这个小说有3章）
    test_novel_id = 7520128677003136024
    
    print(f"\n📖 测试小说ID: {test_novel_id}")
    
    # 使用演示配置
    if os.path.exists('demo_config.yaml'):
        print("📄 加载演示配置文件: demo_config.yaml")
        config = Config.from_yaml('demo_config.yaml')
    else:
        print("📄 使用默认配置（启用TXT和JSON）")
        config = Config()
        config.enable_txt = True
        config.enable_json = True
        config.enable_epub = False  # 暂时关闭，避免复杂度
        config.thread_count = 4
        config.delay_mode = "fast"
    
    # 显示配置信息
    print(f"\n📋 当前配置:")
    print(f"  ✅ TXT: {config.enable_txt}")
    print(f"  ✅ JSON: {config.enable_json}")
    print(f"  ✅ EPUB: {config.enable_epub}")
    print(f"  ⚡ 线程数: {config.thread_count}")
    print(f"  ⏱️  延时: {config.delay_mode} ({config.delay[0]}-{config.delay[1]}ms)")
    
    # 创建下载器
    try:
        print(f"\n🔧 初始化下载器...")
        downloader = NovelDownloader(config)
        print(f"✅ 下载器初始化成功")
        
        # 显示目录信息
        print(f"\n📁 输出目录:")
        if config.enable_txt:
            print(f"  📄 TXT: {downloader.novel_downloads_dir}")
        if config.enable_json:
            print(f"  💾 JSON: {downloader.bookstore_dir}")
        if config.enable_epub:
            print(f"  📚 EPUB: {downloader.epub_dir}")
        
        # 开始下载
        print(f"\n🔽 开始下载...")
        result = downloader.download_novel(test_novel_id)
        
        if result == 's':
            print(f"\n🎉 下载成功完成！")
            
            # 检查生成的文件
            print(f"\n📊 文件检查:")
            
            # 检查TXT目录
            if config.enable_txt and os.path.exists(downloader.novel_downloads_dir):
                txt_files = []
                for root, dirs, files in os.walk(downloader.novel_downloads_dir):
                    for file in files:
                        if file.endswith('.txt'):
                            file_path = os.path.join(root, file)
                            file_size = os.path.getsize(file_path)
                            txt_files.append((file_path, file_size))
                
                print(f"  📄 TXT文件 ({len(txt_files)}个):")
                for file_path, file_size in txt_files:
                    rel_path = os.path.relpath(file_path)
                    print(f"    - {rel_path} ({file_size:,} 字节)")
            
            # 检查JSON目录
            if config.enable_json and os.path.exists(downloader.bookstore_dir):
                json_files = []
                for root, dirs, files in os.walk(downloader.bookstore_dir):
                    for file in files:
                        if file.endswith('.json'):
                            file_path = os.path.join(root, file)
                            file_size = os.path.getsize(file_path)
                            json_files.append((file_path, file_size))
                
                print(f"  💾 JSON文件 ({len(json_files)}个):")
                for file_path, file_size in json_files:
                    rel_path = os.path.relpath(file_path)
                    print(f"    - {rel_path} ({file_size:,} 字节)")
            
            # 检查EPUB目录（如果启用）
            if config.enable_epub and os.path.exists(downloader.epub_dir):
                epub_files = []
                for root, dirs, files in os.walk(downloader.epub_dir):
                    for file in files:
                        if file.endswith('.epub'):
                            file_path = os.path.join(root, file)
                            file_size = os.path.getsize(file_path)
                            epub_files.append((file_path, file_size))
                
                print(f"  📚 EPUB文件 ({len(epub_files)}个):")
                for file_path, file_size in epub_files:
                    rel_path = os.path.relpath(file_path)
                    print(f"    - {rel_path} ({file_size:,} 字节)")
        
        else:
            print(f"❌ 下载失败: {result}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n✨ 多格式下载测试完成！")

if __name__ == "__main__":
    test_multi_format_download() 