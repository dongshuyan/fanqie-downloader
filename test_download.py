#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精简测试下载器 - 专门测试小说ID: 7520128677003136024
"""

import os
import json
import time
import random
import requests as req
from tqdm import tqdm
from lxml import etree

class SimpleDownloader:
    def __init__(self):
        self.headers = {
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.cookie = None
        self.novel_id = 7520128677003136024
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.charset = self.load_charset()
        
    def load_charset(self):
        """加载字符解码映射表"""
        charset_path = os.path.join(self.script_dir, 'src', 'charset.json')
        try:
            with open(charset_path, 'r', encoding='UTF-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  无法加载字符映射表: {e}")
            return [[], []]  # 返回空映射表作为fallback
            
    def decode_content(self, content, mode=0):
        """解码特殊字符"""
        if not self.charset or len(self.charset) < 2:
            return content
            
        charset_map = self.charset[mode]
        result = ""
        
        for char in content:
            char_code = ord(char)
            # 检查是否在需要解码的范围内
            if 58344 <= char_code <= 58715:
                index = char_code - 58344
                if index < len(charset_map):
                    result += charset_map[index]
                else:
                    result += char
            elif 58345 <= char_code <= 58716:
                index = char_code - 58345
                if index < len(charset_map):
                    result += charset_map[index]
                else:
                    result += char
            else:
                result += char
                
        return result
        
    def init_cookie(self):
        """初始化cookie"""
        print("🔑 正在获取cookie...")
        base_timestamp = int(time.time() * 1000)
        self.cookie = f'novel_web_id={base_timestamp}'
        print(f"✅ Cookie获取成功: {self.cookie}")
        
    def get_chapter_list(self):
        """获取章节列表"""
        print("📚 正在获取章节列表...")
        url = f'https://fanqienovel.com/page/{self.novel_id}'
        
        response = req.get(url, headers=self.headers)
        print(f"🌐 响应状态: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ 获取页面失败: HTTP {response.status_code}")
            return None, None, None
            
        # 解析HTML
        ele = etree.HTML(response.text)
        
        # 获取章节列表
        chapters = {}
        a_elements = ele.xpath('//div[@class="chapter"]/div/a')
        
        if not a_elements:
            print("❌ 未找到章节列表")
            return None, None, None
            
        for a in a_elements:
            href = a.xpath('@href')
            if href and a.text:
                chapters[a.text] = href[0].split('/')[-1]
        
        # 获取小说标题和状态
        title_elements = ele.xpath('//h1/text()')
        status_elements = ele.xpath('//span[@class="info-label-yellow"]/text()')
        
        if not title_elements:
            print("❌ 未找到小说标题")
            return None, None, None
            
        name = title_elements[0]
        status = status_elements[0] if status_elements else "未知状态"
        
        print(f"📖 小说名: {name}")
        print(f"📄 章节数: {len(chapters)}")
        print(f"📊 状态: {status}")
        
        return name, chapters, status
        
    def download_chapter_content(self, chapter_id):
        """下载单个章节内容"""
        url = f'https://fanqienovel.com/reader/{chapter_id}'
        headers = self.headers.copy()
        headers['Cookie'] = self.cookie
        
        try:
            response = req.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 解析HTML内容
            ele = etree.HTML(response.text)
            paragraphs = ele.xpath('//div[@class="muye-reader-content noselect"]//p/text()')
            
            if paragraphs:
                content = '\n'.join(paragraphs)
                # 应用字符解码
                decoded_content = self.decode_content(content)
                return decoded_content
            else:
                print(f"⚠️  未找到章节内容: {chapter_id}")
                return None
                
        except Exception as e:
            print(f"❌ 下载章节失败 {chapter_id}: {e}")
            return None
            
    def download_novel(self):
        """下载完整小说"""
        print(f"🚀 开始下载小说ID: {self.novel_id}")
        
        # 初始化cookie
        self.init_cookie()
        
        # 获取章节列表
        name, chapters, status = self.get_chapter_list()
        if not chapters:
            print("❌ 无法获取章节列表")
            return
            
        print(f"\n📥 开始下载《{name}》，状态：{status}")
        
        # 下载所有章节
        novel_content = {}
        failed_chapters = []
        
        with tqdm(total=len(chapters), desc='下载进度') as pbar:
            for title, chapter_id in chapters.items():
                print(f"\n📄 下载章节: {title}")
                content = self.download_chapter_content(chapter_id)
                
                if content is not None and len(content) > 0:
                    novel_content[title] = content
                    print(f"✅ 成功 - 长度: {len(content)} 字符")
                else:
                    failed_chapters.append(title)
                    print(f"❌ 失败: {title}")
                    
                pbar.update(1)
                time.sleep(0.5)  # 避免请求过快
                
        # 显示下载结果
        print(f"\n📊 下载完成统计:")
        print(f"✅ 成功: {len(novel_content)}/{len(chapters)} 章")
        print(f"❌ 失败: {len(failed_chapters)} 章")
        
        if failed_chapters:
            print(f"失败章节: {failed_chapters}")
            
        # 生成文件
        if novel_content:
            self.save_files(name, novel_content)
        else:
            print("❌ 没有成功下载任何章节，无法生成文件")
            
    def save_files(self, name, content):
        """保存文件"""
        print(f"\n💾 开始保存文件...")
        
        # 清理文件名
        safe_name = self.sanitize_filename(name)
        
        # 保存JSON文件（备份）
        json_path = f"{safe_name}.json"
        with open(json_path, 'w', encoding='UTF-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON文件已保存: {json_path}")
        
        # 保存TXT文件（阅读用）
        txt_path = f"{safe_name}.txt"
        with open(txt_path, 'w', encoding='UTF-8') as f:
            f.write(f"《{name}》\n")
            f.write("="*50 + "\n\n")
            
            for title, chapter_content in content.items():
                f.write(f"\n{title}\n")
                f.write("-"*30 + "\n")
                f.write(f"{chapter_content}\n\n")
                
        print(f"✅ TXT文件已保存: {txt_path}")
        
        # 验证文件
        if os.path.exists(txt_path):
            file_size = os.path.getsize(txt_path)
            print(f"📁 TXT文件大小: {file_size} 字节")
            
            # 读取前100个字符预览
            with open(txt_path, 'r', encoding='UTF-8') as f:
                preview = f.read(200)
                print(f"📖 文件预览:\n{preview}...")
        else:
            print("❌ TXT文件未能成功创建")
            
    def sanitize_filename(self, filename):
        """清理文件名"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename

def main():
    print("🔥 精简测试下载器启动")
    print("📋 目标小说ID: 7520128677003136024")
    print("🎯 功能: 下载小说并生成TXT文件")
    print("-"*50)
    
    downloader = SimpleDownloader()
    downloader.download_novel()
    
    print("\n🎉 测试完成！")
    print("📁 请检查当前目录下的文件:")
    print("   - *.json (备份文件)")
    print("   - *.txt (阅读文件)")

if __name__ == "__main__":
    main() 