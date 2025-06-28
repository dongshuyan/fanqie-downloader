# -*- coding: utf-8 -*-
"""
修复版main.py - 解决cookie生成时的巨大循环卡死问题
原版本在_get_new_cookie函数中使用6×10^18到9×10^18的巨大循环范围，导致程序卡住
修复版本使用基于时间戳的合理范围，避免长时间等待
"""
import requests as req
from lxml import etree
from ebooklib import epub
from tqdm import tqdm
from bs4 import BeautifulSoup
import json
import yaml  # 添加YAML支持
import time
import random
import re  # 添加正则表达式模块
import os
import platform
import shutil
import concurrent.futures
import argparse  # 添加命令行参数解析
from typing import Callable, Optional, Dict, List, Union
from dataclasses import dataclass, field
from enum import Enum


class SaveMode(Enum):
    SINGLE_TXT = 1
    SPLIT_TXT = 2
    EPUB = 3
    HTML = 4
    LATEX = 5


@dataclass
class Config:
    # 文件格式控制
    enable_txt: bool = True
    enable_epub: bool = False
    enable_html: bool = False
    enable_latex: bool = False
    enable_pdf: bool = False
    
    # 目录配置 (简化版)
    bookstore_dir: str = "bookstore"    # JSON文件存放目录
    download_dir: str = "downloads"     # 其他格式文件存放目录
    
    # 性能配置
    thread_count: int = 8
    delay_mode: str = "normal"
    custom_delay: List[int] = field(default_factory=lambda: [150, 300])
    
    # 文件管理
    delete_chapters_after_merge: bool = False
    conflict_resolution: str = "rename"
    encoding: str = "UTF-8"
    preserve_original_order: bool = False
    
    # Cookie配置
    cookie_mode: str = "auto"
    manual_cookie: str = ""
    cookie_file: str = "data/cookie.json"
    validate_cookie: bool = False
    
    # 内容处理
    paragraph_spacing: int = 0
    indent_character: str = "　"
    decode_mode: str = "auto"
    filter_special_chars: bool = False
    
    # 网络配置
    timeout: int = 30
    retry_count: int = 3
    retry_delays: List[int] = field(default_factory=lambda: [1, 2, 4])  # 重试间隔(秒)
    rotate_user_agent: bool = True
    
    # 日志配置
    log_level: str = "normal"
    save_log_to_file: bool = False
    log_file: str = "logs/download.log"
    
    # 高级选项
    enable_experimental: bool = False
    memory_mode: str = "normal"
    show_progress_bar: bool = True
    
    # 兼容性字段（保持向后兼容）
    kg: int = 0
    kgf: str = '　'
    delay: List[int] = field(default_factory=lambda: [100, 200])
    save_path: str = ''
    save_mode: SaveMode = SaveMode.SINGLE_TXT
    space_mode: str = 'halfwidth'
    xc: int = 8
    
    def __post_init__(self):
        # 处理延时配置
        if self.delay_mode == "fast":
            self.delay = [50, 100]
        elif self.delay_mode == "normal":
            self.delay = [100, 200]
        elif self.delay_mode == "safe":
            self.delay = [200, 500]
        elif self.delay_mode == "custom":
            self.delay = self.custom_delay.copy()
        
        # 同步线程数配置
        self.xc = self.thread_count
        
        # 同步段落配置
        self.kg = self.paragraph_spacing
        self.kgf = self.indent_character
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'Config':
        """从YAML文件加载配置"""
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            config = cls()
            
            # 文件格式配置
            if 'formats' in data:
                formats = data['formats']
                config.enable_txt = formats.get('enable_txt', True)
                config.enable_epub = formats.get('enable_epub', False)
                config.enable_html = formats.get('enable_html', False)
                config.enable_latex = formats.get('enable_latex', False)
                config.enable_pdf = formats.get('enable_pdf', False)
            
            # 目录配置 (简化版)
            if 'directories' in data:
                dirs = data['directories']
                config.bookstore_dir = dirs.get('bookstore_dir', "bookstore")
                config.download_dir = dirs.get('download_dir', "downloads")
            
            # 性能配置
            if 'performance' in data:
                perf = data['performance']
                config.thread_count = perf.get('thread_count', 8)
                config.delay_mode = perf.get('delay_mode', "normal")
                config.custom_delay = perf.get('custom_delay', [150, 300])
            
            # 文件管理配置
            if 'file_management' in data:
                fm = data['file_management']
                config.delete_chapters_after_merge = fm.get('delete_chapters_after_merge', False)
                config.conflict_resolution = fm.get('conflict_resolution', "rename")
                config.encoding = fm.get('encoding', "UTF-8")
                config.preserve_original_order = fm.get('preserve_original_order', False)
            
            # Cookie配置
            if 'authentication' in data:
                auth = data['authentication']
                config.cookie_mode = auth.get('cookie_mode', "auto")
                config.manual_cookie = auth.get('manual_cookie', "")
                config.cookie_file = auth.get('cookie_file', "data/cookie.json")
                config.validate_cookie = auth.get('validate_cookie', False)
            
            # 内容处理配置
            if 'content' in data:
                content = data['content']
                config.paragraph_spacing = content.get('paragraph_spacing', 0)
                config.indent_character = content.get('indent_character', "　")
                config.decode_mode = content.get('decode_mode', "auto")
                config.filter_special_chars = content.get('filter_special_chars', False)
            
            # 网络配置
            if 'network' in data:
                net = data['network']
                config.timeout = net.get('timeout', 30)
                config.retry_count = net.get('retry_count', 3)
                config.retry_delays = net.get('retry_delays', [1, 2, 4])
                config.rotate_user_agent = net.get('rotate_user_agent', True)
            
            # 日志配置
            if 'logging' in data:
                log = data['logging']
                config.log_level = log.get('level', "normal")
                config.save_log_to_file = log.get('save_to_file', False)
                config.log_file = log.get('log_file', "logs/download.log")
            
            # 高级配置
            if 'advanced' in data:
                adv = data['advanced']
                config.enable_experimental = adv.get('enable_experimental', False)
                config.memory_mode = adv.get('memory_mode', "normal")
                config.show_progress_bar = adv.get('show_progress_bar', True)
            
            return config
            
        except Exception as e:
            print(f"⚠️ 配置文件读取失败: {e}")
            print("使用默认配置")
            return cls()
    
    def get_delay_range(self) -> List[int]:
        """获取当前的延时范围"""
        return self.delay


class NovelDownloader:
    def __init__(self,
                 config: Config,
                 progress_callback: Optional[Callable] = None,
                 log_callback: Optional[Callable] = None):
        self.config = config
        self.progress_callback = progress_callback or self._default_progress
        self.log_callback = log_callback or print

        # Initialize headers first
        self.headers_lib = [
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36'},
            {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0'},
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36 Edg/93.0.961.47'}
        ]
        self.headers = random.choice(self.headers_lib)

        # Use absolute paths based on script location
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.script_dir, 'data')
        
        # 使用配置文件中的目录设置 (简化版)
        self.bookstore_dir = os.path.join(self.script_dir, self.config.bookstore_dir)  # JSON文件目录
        self.download_dir = os.path.join(self.script_dir, self.config.download_dir)    # 其他格式文件目录
        
        self.record_path = os.path.join(self.data_dir, 'record.json')
        self.config_path = os.path.join(self.data_dir, 'config.json')
        
        # Cookie路径根据配置决定
        if self.config.cookie_mode == "file":
            self.cookie_path = os.path.join(self.script_dir, self.config.cookie_file)
        else:
            self.cookie_path = os.path.join(self.data_dir, 'cookie.json')

        self.CODE = [[58344, 58715], [58345, 58716]]

        # Load charset for text decoding
        charset_path = os.path.join(self.script_dir, 'charset.json')
        with open(charset_path, 'r', encoding='UTF-8') as f:
            self.charset = json.load(f)

        self._setup_directories()
        self._init_cookie()

        # Add these variables
        self.zj = {}  # For storing chapter data
        self.cs = 0  # Chapter counter
        self.tcs = 0  # Test counter
        self.tzj = None  # Test chapter ID
        self.book_json_path = None  # Current book's JSON path
        
        # 反爬检测和自适应延时
        self.empty_content_count = 0  # 连续空内容计数
        self.total_empty_count = 0    # 总计空内容计数
        self.adaptive_delay_multiplier = 1.0  # 自适应延时倍数
        self.last_successful_time = time.time()  # 上次成功时间
        
        # 🔄 策略2：成功下载计数器（用于主动Cookie刷新）
        self.successful_downloads = 0
        
        # 📝 失败章节记录（用于生成error.log）
        self.failed_chapters = []  # 格式: [{'title': str, 'chapter_id': str, 'reason': str}]

    def _setup_directories(self):
        """Create necessary directories if they don't exist"""
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 创建基础目录
        os.makedirs(self.bookstore_dir, exist_ok=True)  # JSON文件目录（总是需要）
        os.makedirs(self.download_dir, exist_ok=True)   # 其他格式文件目录
            
        # 如果需要保存日志，创建日志目录
        if self.config.save_log_to_file:
            log_dir = os.path.dirname(os.path.join(self.script_dir, self.config.log_file))
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)

    def _init_cookie(self):
        """Initialize cookie for downloads - 简化版本，直接使用默认cookie"""
        self.log_callback('正在初始化cookie')
        
        # 直接使用时间戳生成默认cookie，无需验证
        base_timestamp = int(time.time() * 1000)
        self.cookie = f'novel_web_id={base_timestamp}'
        
        # 保存cookie到文件
        try:
            with open(self.cookie_path, 'w', encoding='UTF-8') as f:
                json.dump(self.cookie, f)
        except Exception:
            pass  # 忽略保存失败，继续使用内存中的cookie
            
        self.log_callback('Cookie初始化完成')

    def _default_progress(self, current: int, total: int, desc: str = '',
                          chapter_title: str = None):
        """Progress tracking for both CLI and web"""
        # For CLI: Don't create additional progress bar, tqdm is already handled in download_novel
        # For web: Return progress info as dict
        return {
            'current': current,
            'total': total,
            'percentage': (current / total * 100) if total > 0 else 0,
            'description': desc,
            'chapter_title': chapter_title
        }
    
    def _write_debug_log(self, message: str):
        """写入调试日志到文件和控制台"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        
        # 输出到控制台（如果启用了详细日志）
        if hasattr(self.config, 'log_level') and self.config.log_level == 'debug':
            self.log_callback(log_message)
        
        # 写入日志文件
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "download_debug.log")
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_message + '\n')
        except Exception as e:
            # 避免日志写入失败影响主程序
            pass

    def _get_randomized_headers(self) -> Dict[str, str]:
        """🎭 策略3：生成高度真实化的随机请求头，模拟真实用户行为（20+种变化）"""
        
        # 🌟 大幅扩展User-Agent池（20+种真实浏览器）
        user_agents = [
            # Chrome最新版本 - Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
            
            # Chrome - macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            
            # Safari - macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
            
            # Firefox - Windows & macOS
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
            
            # Edge - Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            
            # 移动端User-Agent（偶尔使用增加真实性）
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36',
            
            # 一些稍旧但仍然真实的版本
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        ]
        
        # 🌐 扩展Accept-Language池（真实地区变化）
        accept_languages = [
            'zh-CN,zh;q=0.9,en;q=0.8',
            'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
            'zh-CN,zh;q=0.9',
            'zh,en-US;q=0.8,en;q=0.6',
            'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'zh-CN,zh-TW;q=0.9,zh;q=0.8,en;q=0.7',
            'zh-CN,zh;q=0.8,en;q=0.6,ja;q=0.4',
            'zh-CN,zh;q=0.9,en-GB;q=0.8,en;q=0.7,zh-TW;q=0.6'
        ]
        
        # 📋 扩展Accept池（更真实的浏览器行为）
        accepts = [
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9'
        ]
        
        # 🗜️ 扩展Accept-Encoding池
        accept_encodings = [
            'gzip, deflate, br',
            'gzip, deflate',
            'gzip, deflate, br, zstd',
            'gzip, deflate, br',
            'gzip, deflate, compress, br',
            'gzip, br, deflate'
        ]
        
        # 🔗 真实的Connection选项
        connections = ['keep-alive', 'close']
        
        # 💾 真实的Cache-Control选项
        cache_controls = [
            'no-cache',
            'max-age=0',
            'no-store',
            'max-age=0, no-cache',
            'no-cache, no-store, must-revalidate',
            'max-age=3600'
        ]
        
        # 🌍 真实的Referer选项（模拟从不同页面访问）
        referers = [
            'https://fanqienovel.com/',
            'https://fanqienovel.com/page',
            'https://www.google.com/',
            'https://www.baidu.com/',
            'https://fanqienovel.com/search',
            None  # 有时候没有referer
        ]
        
        # 🔒 真实的Sec-Fetch系列
        sec_fetch_dests = ['document', 'empty', 'iframe']
        sec_fetch_modes = ['navigate', 'cors', 'no-cors', 'same-origin']  
        sec_fetch_sites = ['none', 'same-origin', 'same-site', 'cross-site']
        sec_fetch_users = ['?1', None]  # 有时候没有这个头
        
        # 🎯 选择User-Agent并基于它确定浏览器类型
        selected_ua = random.choice(user_agents)
        is_chrome = 'Chrome' in selected_ua and 'Edg' not in selected_ua
        is_firefox = 'Firefox' in selected_ua
        is_safari = 'Safari' in selected_ua and 'Chrome' not in selected_ua
        is_edge = 'Edg' in selected_ua
        is_mobile = 'Mobile' in selected_ua
        
        base_headers = self.headers.copy()
        
        # 🎭 构建真实的随机化请求头
        randomized_headers = {
            **base_headers,
            'User-Agent': selected_ua,
            'Accept': random.choice(accepts),
            'Accept-Language': random.choice(accept_languages),
            'Accept-Encoding': random.choice(accept_encodings),
            'Connection': random.choice(connections),
            'Cache-Control': random.choice(cache_controls),
        }
        
        # 🌍 随机添加Referer（80%概率）
        if random.random() > 0.2:
            referer = random.choice(referers)
            if referer:
                randomized_headers['Referer'] = referer
        
        # 🔒 Chrome/Edge特有的Sec-Fetch头部
        if is_chrome or is_edge:
            randomized_headers['Sec-Fetch-Dest'] = random.choice(sec_fetch_dests)
            randomized_headers['Sec-Fetch-Mode'] = random.choice(sec_fetch_modes)
            randomized_headers['Sec-Fetch-Site'] = random.choice(sec_fetch_sites)
            
            # Sec-Fetch-User（导航时才有）
            if random.choice(sec_fetch_users):
                randomized_headers['Sec-Fetch-User'] = '?1'
                
            # Sec-CH系列（Chrome特有）
            if is_chrome and random.random() > 0.5:
                randomized_headers['Sec-CH-UA'] = '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"'
                randomized_headers['Sec-CH-UA-Mobile'] = '?1' if is_mobile else '?0'
                randomized_headers['Sec-CH-UA-Platform'] = f'"{random.choice(["Windows", "macOS", "Linux"])}"'
        
        # 🚫 DNT头部（60%概率）
        if random.random() > 0.4:
            randomized_headers['DNT'] = '1'
        
        # 🔒 Upgrade-Insecure-Requests（70%概率）
        if random.random() > 0.3:
            randomized_headers['Upgrade-Insecure-Requests'] = '1'
            
        # 📱 移动端特有头部
        if is_mobile:
            randomized_headers['Viewport-Width'] = str(random.choice([375, 414, 390, 393]))
            if random.random() > 0.5:
                randomized_headers['Device-Memory'] = str(random.choice([4, 6, 8]))
        
        # 🕰️ Pragma头部（偶尔添加，10%概率）
        if random.random() > 0.9:
            randomized_headers['Pragma'] = 'no-cache'
            
        # 🌍 Host头部（总是设置为目标站点）
        randomized_headers['Host'] = 'fanqienovel.com'
        
        # 🔧 浏览器特有的其他头部
        
        # Firefox特有
        if is_firefox and random.random() > 0.7:
            randomized_headers['Accept-Language'] = randomized_headers['Accept-Language'].replace('q=0.', 'q=0.')
            
        # Safari特有  
        if is_safari and random.random() > 0.6:
            randomized_headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            
        # 随机移除某些可选头部（模拟不同浏览器配置）
        optional_headers = ['DNT', 'Pragma', 'Sec-CH-UA', 'Device-Memory', 'Viewport-Width']
        for header in optional_headers:
            if header in randomized_headers and random.random() > 0.8:
                del randomized_headers[header]
        
        # 📊 记录使用的请求头类型（用于调试）
        browser_type = 'Chrome' if is_chrome else 'Firefox' if is_firefox else 'Safari' if is_safari else 'Edge' if is_edge else 'Unknown'
        self._write_debug_log(f"🎭 使用{browser_type}请求头模拟，共{len(randomized_headers)}个头部")
        
        return randomized_headers

    def _smart_reading_pause(self, chapter_title: str = ""):
        """🎭 策略3：模拟真实阅读行为的随机暂停 (0-5秒)"""
        pause_duration = random.uniform(0, 5.0)  # 0到5秒的随机暂停
        
        if pause_duration > 0.1:  # 只记录超过0.1秒的暂停
            self._write_debug_log(f"🎭 模拟阅读暂停 {pause_duration:.2f}秒 {'- ' + chapter_title if chapter_title else ''}")
        
        time.sleep(pause_duration)

    def _should_refresh_cookie_proactively(self) -> bool:
        """🔄 策略2：检查是否应该主动刷新Cookie"""
        # 🚨 更激进：每20个章节主动刷新一次
        return hasattr(self, 'successful_downloads') and self.successful_downloads > 0 and self.successful_downloads % 20 == 0

    def _generate_error_log(self, output_dir: str):
        """📝 生成error.log文件记录最终失败的章节"""
        if not self.failed_chapters:
            return  # 没有失败章节就不生成
        
        error_log_path = os.path.join(output_dir, "error.log")
        
        try:
            with open(error_log_path, 'w', encoding='utf-8') as f:
                f.write("# 章节下载失败记录\n")
                f.write(f"# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 失败章节总数: {len(self.failed_chapters)}\n")
                f.write("# 格式: 章节标题 | 章节ID | 失败原因\n")
                f.write("=" * 80 + "\n\n")
                
                for failed in self.failed_chapters:
                    title = failed.get('title', '未知标题')
                    chapter_id = failed.get('chapter_id', '未知ID')
                    reason = failed.get('reason', '未知原因')
                    f.write(f"{title} | {chapter_id} | {reason}\n")
            
            self.log_callback(f"📝 已生成失败章节记录: {error_log_path} ({len(self.failed_chapters)}个失败章节)")
            self._write_debug_log(f"📝 error.log已生成: {error_log_path}")
            
        except Exception as e:
            self.log_callback(f"⚠️ 生成error.log失败: {str(e)}")
            self._write_debug_log(f"⚠️ 生成error.log失败: {str(e)}")

    def download_novel(self, novel_id: int) -> str:
        """Download a novel"""
        try:
            # 📝 重置失败章节记录（每个小说单独记录）
            self.failed_chapters = []
            
            name, chapters, status = self._get_chapter_list(novel_id)
            if name == 'err':
                return 'err'

            safe_name = self._sanitize_filename(name)
            self.log_callback(f'\n开始下载《{name}》，状态：{status[0]}')

            # 创建"书名-id"文件夹结构
            book_folder_name = f"{safe_name}-{novel_id}"
            book_download_dir = os.path.join(self.download_dir, book_folder_name)    # 其他格式文件目录
            book_json_dir = os.path.join(self.bookstore_dir, book_folder_name)       # JSON文件目录
            chapters_dir = os.path.join(book_download_dir, "Chapters")
            
            # 创建必需的目录
            os.makedirs(book_download_dir, exist_ok=True)
            os.makedirs(book_json_dir, exist_ok=True) 
            os.makedirs(chapters_dir, exist_ok=True)
            
            self.log_callback(f'创建文件夹: {book_folder_name}')

            # 使用原始章节列表的顺序
            chapter_list = list(chapters.items())  # 转换为列表保持顺序
            total_chapters = len(chapter_list)
            completed_chapters = 0

            # 创建一个有序字典来保存章节内容
            novel_content = {}

            # 下载章节
            with tqdm(total=total_chapters, desc='下载进度') as pbar:
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.xc) as executor:
                    future_to_chapter = {
                        executor.submit(
                            self._download_chapter,
                            title,
                            chapter_id,
                            {}
                        ): (title, chapter_id) for title, chapter_id in chapter_list
                    }

                    for future in concurrent.futures.as_completed(future_to_chapter):
                        title, chapter_id = future_to_chapter[future]
                        try:
                            content = future.result()
                            if content:
                                # 记录详细的章节下载信息
                                self._write_debug_log(f"✅ 成功下载章节: 「{title}」(ID: {chapter_id}) - 内容长度: {len(content)} 字符")
                                
                                # 🚨 关键调试点：检查标题处理过程
                                self._write_debug_log(f"🔍 【文件保存调试】开始处理章节文件保存")
                                self._write_debug_log(f"🔍 原始title: {repr(title)} (类型: {type(title).__name__})")
                                
                                clean_title = title.strip()
                                self._write_debug_log(f"🔍 clean_title: {repr(clean_title)} (类型: {type(clean_title).__name__})")
                                
                                novel_content[clean_title] = content
                                
                                # 🚨 关键调试点：文件名生成过程
                                self._write_debug_log(f"🔍 调用_sanitize_filename前: {repr(clean_title)}")
                                sanitized_title = self._sanitize_filename(clean_title)
                                self._write_debug_log(f"🔍 _sanitize_filename返回: {repr(sanitized_title)} (类型: {type(sanitized_title).__name__})")
                                
                                chapter_filename = f"{sanitized_title}.txt"
                                self._write_debug_log(f"🔍 chapter_filename: {repr(chapter_filename)} (类型: {type(chapter_filename).__name__})")
                                
                                # 🚨 关键调试点：路径拼接过程
                                self._write_debug_log(f"🔍 chapters_dir: {repr(chapters_dir)} (类型: {type(chapters_dir).__name__})")
                                self._write_debug_log(f"🔍 准备调用os.path.join({repr(chapters_dir)}, {repr(chapter_filename)})")
                                
                                chapter_path = os.path.join(chapters_dir, chapter_filename)
                                self._write_debug_log(f"🔍 chapter_path: {repr(chapter_path)} (类型: {type(chapter_path).__name__})")
                                
                                # 🚨 关键调试点：文件写入过程
                                self._write_debug_log(f"🔍 准备打开文件: {repr(chapter_path)}")
                                with open(chapter_path, 'w', encoding='UTF-8') as f:
                                    f.write(f"{clean_title}\n\n{content}")
                                self._write_debug_log(f"✅ 章节文件保存成功: {chapter_path}")
                            else:
                                # 内容为空的情况
                                self._write_debug_log(f"⚠️ 章节内容为空: 「{title}」(ID: {chapter_id})")
                                self.log_callback(f"⚠️ 章节「{title}」下载失败: 内容为空")
                                    
                        except Exception as e:
                            # 🚨🚨🚨 完整的错误信息输出 - 用户强调的关键需求！🚨🚨🚨
                            self._write_debug_log(f"❌❌❌ 【完整错误报告】章节下载异常: 「{title}」(ID: {chapter_id}) ❌❌❌")
                            self._write_debug_log(f"=" * 100)
                            
                            # 基本信息
                            self._write_debug_log(f"🔍 标题信息:")
                            self._write_debug_log(f"   - 标题类型: {type(title).__name__}")
                            self._write_debug_log(f"   - 标题内容: {repr(title)}")
                            self._write_debug_log(f"   - 标题长度: {len(title) if title else 'None'}")
                            self._write_debug_log(f"🔍 章节ID信息:")
                            self._write_debug_log(f"   - 章节ID类型: {type(chapter_id).__name__}")
                            self._write_debug_log(f"   - 章节ID内容: {repr(chapter_id)}")
                            
                            # 错误详情
                            self._write_debug_log(f"❌ 错误详情:")
                            self._write_debug_log(f"   - 错误类型: {type(e).__name__}")
                            self._write_debug_log(f"   - 错误详情: {str(e)}")
                            self._write_debug_log(f"   - 错误参数: {getattr(e, 'args', 'No args')}")
                            self._write_debug_log(f"   - 完整异常信息: {repr(e)}")
                            
                            # 🚨 关键：尝试获取该章节的完整响应内容
                            self._write_debug_log(f"🌐 尝试获取该章节的完整网络响应:")
                            try:
                                # 强制获取该章节的原始响应
                                test_content = self._download_chapter_content(int(chapter_id), test_mode=True)
                                self._write_debug_log(f"📥 原始响应内容类型: {type(test_content).__name__}")
                                self._write_debug_log(f"📥 原始响应长度: {len(test_content) if test_content else 'None'}")
                                self._write_debug_log(f"📥 原始响应前500字符: {repr(test_content[:500]) if test_content else 'None'}")
                                if test_content and len(test_content) > 500:
                                    self._write_debug_log(f"📥 原始响应后200字符: {repr(test_content[-200:])}")
                                self._write_debug_log(f"📥 完整原始响应: {repr(test_content)}")
                            except Exception as response_error:
                                self._write_debug_log(f"💥 获取原始响应失败: {str(response_error)}")
                                self._write_debug_log(f"💥 响应错误类型: {type(response_error).__name__}")
                                self._write_debug_log(f"💥 响应错误详情: {repr(response_error)}")
                            
                            # 环境状态信息
                            self._write_debug_log(f"🌍 环境状态:")
                            self._write_debug_log(f"   - chapters_dir: {repr(chapters_dir)}")
                            self._write_debug_log(f"   - chapters_dir类型: {type(chapters_dir).__name__}")
                            self._write_debug_log(f"   - chapters_dir存在: {os.path.exists(chapters_dir) if chapters_dir else 'chapters_dir is None'}")
                            self._write_debug_log(f"   - 当前工作目录: {repr(os.getcwd())}")
                            
                            # 局部变量状态
                            self._write_debug_log(f"📊 局部变量状态:")
                            local_vars = ['content', 'clean_title', 'sanitized_title', 'chapter_filename', 'chapter_path']
                            for var_name in local_vars:
                                if var_name in locals():
                                    var_value = locals()[var_name]
                                    self._write_debug_log(f"   - {var_name}: {repr(var_value)} (类型: {type(var_value).__name__})")
                                else:
                                    self._write_debug_log(f"   - {var_name}: 未定义")
                            
                            # 特殊处理路径相关错误
                            if "PathLike" in str(e) or "NoneType" in str(e):
                                self._write_debug_log(f"🚨 检测到路径或NoneType错误 - 深度分析:")
                                
                                # 测试_sanitize_filename函数
                                try:
                                    test_title = title.strip() if title else "ERROR_None_Title"
                                    sanitized = self._sanitize_filename(test_title)
                                    self._write_debug_log(f"   🔧 _sanitize_filename测试: {repr(test_title)} -> {repr(sanitized)}")
                                except Exception as sanitize_error:
                                    self._write_debug_log(f"   💥 _sanitize_filename测试失败: {str(sanitize_error)}")
                                    self._write_debug_log(f"   💥 _sanitize_filename错误详情: {repr(sanitize_error)}")
                            
                            self._write_debug_log(f"=" * 100)
                            self._write_debug_log(f"❌❌❌ 【完整错误报告结束】 ❌❌❌")
                            
                            # 📝 记录最终失败的章节（用于生成error.log）
                            failure_reason = self._get_failure_reason(e)
                            self.failed_chapters.append({
                                'title': title,
                                'chapter_id': chapter_id,
                                'reason': failure_reason
                            })
                            
                            # 📝 1. 创建占位TXT文件
                            try:
                                clean_title = title.strip() if title else f"第{chapter_id}章"
                                sanitized_title = self._sanitize_filename(clean_title)
                                chapter_filename = f"{sanitized_title}.txt"
                                chapter_path = os.path.join(chapters_dir, chapter_filename)
                                
                                with open(chapter_path, 'w', encoding='UTF-8') as f:
                                    f.write(f"{clean_title}\n\n抓取内容为空")
                                
                                self._write_debug_log(f"📝 已创建失败章节占位文件: {chapter_path}")
                                
                                # 📝 2. 添加占位内容到novel_content（用于JSON和合并TXT）
                                novel_content[clean_title] = "抓取内容为空"
                                
                            except Exception as placeholder_error:
                                self._write_debug_log(f"⚠️ 创建占位文件失败: {str(placeholder_error)}")
                            
                            # 输出到控制台让用户看到真正的问题
                            self.log_callback(f'❌ 下载章节失败「{title}」: {failure_reason}（已创建占位文件）')
                            
                            # 继续处理其他章节，但保留完整的错误记录

                        completed_chapters += 1
                        pbar.update(1)
                        self.progress_callback(
                            completed_chapters,
                            total_chapters,
                            '下载进度',
                            title
                        )

            # 根据配置决定保存哪些格式
            results = []
            
            # 保存JSON文件（必须要的）
            json_path = os.path.join(book_json_dir, f'{safe_name}.json')
            with open(json_path, 'w', encoding='UTF-8') as f:
                json.dump(novel_content, f, ensure_ascii=False, indent=4)
            self.log_callback(f'✅ JSON文件已保存: {json_path}')
            results.append('json')
            
            # 保存TXT文件（如果启用）
            if self.config.enable_txt:
                result = self._save_single_txt_to_folder(safe_name, novel_content, book_download_dir)
                if result == 's':
                    self.log_callback(f'✅ TXT文件已保存')
                    results.append('txt')
                    
                    # 如果配置要求删除章节文件夹
                    if self.config.delete_chapters_after_merge:
                        try:
                            import shutil
                            shutil.rmtree(chapters_dir)
                            self.log_callback(f'🗑️ 已删除章节文件夹: {chapters_dir}')
                        except Exception as e:
                            self.log_callback(f'⚠️ 删除章节文件夹失败: {e}')
            
            # 保存EPUB文件（如果启用）
            if self.config.enable_epub:
                try:
                    epub_result = self._save_epub_from_content(safe_name, novel_content, book_download_dir, novel_id)
                    if epub_result == 's':
                        self.log_callback(f'✅ EPUB文件已保存')
                        results.append('epub')
                except Exception as e:
                    self.log_callback(f'⚠️ EPUB保存失败: {e}')
            
            # 保存HTML文件（如果启用）
            if self.config.enable_html:
                try:
                    html_result = self._save_html_from_content(safe_name, novel_content, book_download_dir)
                    if html_result == 's':
                        self.log_callback(f'✅ HTML文件已保存')
                        results.append('html')
                except Exception as e:
                    self.log_callback(f'⚠️ HTML保存失败: {e}')
            
            # 保存LaTeX文件（如果启用）
            if self.config.enable_latex:
                try:
                    latex_result = self._save_latex_from_content(safe_name, novel_content, book_download_dir)
                    if latex_result == 's':
                        self.log_callback(f'✅ LaTeX文件已保存')
                        results.append('latex')
                        
                        # 如果也启用了PDF，从LaTeX生成PDF
                        if self.config.enable_pdf:
                            try:
                                pdf_result = self._generate_pdf_from_latex(safe_name, book_download_dir)
                                if pdf_result == 's':
                                    self.log_callback(f'✅ PDF文件已保存')
                                    results.append('pdf')
                            except Exception as e:
                                self.log_callback(f'⚠️ PDF生成失败: {e}')
                except Exception as e:
                    self.log_callback(f'⚠️ LaTeX保存失败: {e}')
            elif self.config.enable_pdf:
                # 如果只启用了PDF而没有启用LaTeX，先生成LaTeX再转PDF
                try:
                    latex_result = self._save_latex_from_content(safe_name, novel_content, book_download_dir)
                    if latex_result == 's':
                        pdf_result = self._generate_pdf_from_latex(safe_name, book_download_dir)
                        if pdf_result == 's':
                            self.log_callback(f'✅ PDF文件已保存')
                            results.append('pdf')
                            # 删除临时LaTeX文件
                            try:
                                latex_path = os.path.join(book_download_dir, f'{safe_name}.tex')
                                if os.path.exists(latex_path):
                                    os.remove(latex_path)
                            except:
                                pass
                except Exception as e:
                    self.log_callback(f'⚠️ PDF生成失败: {e}')
            
            # 📝 生成error.log文件（如果有失败章节）
            self._generate_error_log(book_download_dir)
            
            # 返回结果
            if results:
                self.log_callback(f'🎉 下载完成！已保存格式: {", ".join(results)}')
                if self.failed_chapters:
                    self.log_callback(f'⚠️ 注意：有 {len(self.failed_chapters)} 个章节下载失败，已创建占位文件，详情请查看 error.log')
                return 's'
            else:
                self.log_callback(f'⚠️ 未启用任何输出格式')
                return 'err'

        except Exception as e:
            self.log_callback(f'下载失败: {str(e)}')
            return 'err'

    def search_novel(self, keyword: str) -> List[Dict]:
        """
        Search for novels by keyword
        Returns list of novel info dictionaries
        """
        if not keyword:
            return []

        # Use the correct API endpoint from ref_main.py
        url = f"https://api5-normal-lf.fqnovel.com/reading/bookapi/search/page/v/"
        params = {
            "query": keyword,
            "aid": "1967",
            "channel": "0",
            "os_version": "0",
            "device_type": "0",
            "device_platform": "0",
            "iid": "466614321180296",
            "passback": "{(page-1)*10}",
            "version_code": "999"
        }

        try:
            response = req.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            if data['code'] == 0 and data['data']:
                return data['data']
            else:
                self.log_callback("没有找到相关书籍。")
                return []

        except req.RequestException as e:
            self.log_callback(f"网络请求失败: {str(e)}")
            return []
        except json.JSONDecodeError as e:
            self.log_callback(f"解析搜索结果失败: {str(e)}")
            return []
        except Exception as e:
            self.log_callback(f'搜索失败: {str(e)}')
            return []

    # ... Additional helper methods would go here ...

    def _get_initial_chapter_id(self) -> int:
        """Get an initial chapter ID for cookie testing"""
        test_novel_id = 7143038691944959011  # Example novel ID
        chapters = self._get_chapter_list(test_novel_id)
        if chapters and len(chapters[1]) > 21:
            return int(random.choice(list(chapters[1].values())[21:]))
        raise Exception("Failed to get initial chapter ID")

    def _get_new_cookie(self, chapter_id: int):
        """Generate new cookie - 优化版本，减少验证次数"""
        base_timestamp = int(time.time() * 1000)
        
        # 只尝试5次，减少等待时间
        for i in range(5):
            cookie_id = base_timestamp + random.randint(1000, 999999)
            time.sleep(0.1)  # 减少延迟到100ms
            self.cookie = f'novel_web_id={cookie_id}'
            
            try:
                if len(self._download_chapter_content(chapter_id, test_mode=True)) > 200:
                    with open(self.cookie_path, 'w', encoding='UTF-8') as f:
                        json.dump(self.cookie, f)
                    return
            except:
                continue
        
        # 快速失败，使用默认cookie
        self.cookie = f'novel_web_id={base_timestamp}'
        print("⚠️ Cookie生成失败，使用默认值")

    def _download_txt(self, novel_id: int) -> str:
        """Download novel in TXT format"""
        try:
            name, chapters, status = self._get_chapter_list(novel_id)
            if name == 'err':
                return 'err'

            safe_name = self._sanitize_filename(name)
            self.log_callback(f'\n开始下载《{name}》，状态：{status[0]}')

            # Set book_json_path for the current download
            self.book_json_path = os.path.join(self.bookstore_dir, f'{safe_name}.json')

            # Initialize global variables for this download
            self.zj = {}
            self.cs = 0
            self.tcs = 0

            # Store metadata at the start
            metadata = {
                '_metadata': {
                    'novel_id': str(novel_id),  # 确保存储为字符串
                    'name': name,
                    'status': status[0] if status else None,
                    'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
                }
            }

            # Load existing content and merge with metadata
            existing_content = {}
            if os.path.exists(self.book_json_path):
                with open(self.book_json_path, 'r', encoding='UTF-8') as f:
                    existing_content = json.load(f)
                    # Keep existing chapters but update metadata
                    if isinstance(existing_content, dict):
                        existing_content.update(metadata)
            else:
                existing_content = metadata
                # Save initial metadata
                with open(self.book_json_path, 'w', encoding='UTF-8') as f:
                    json.dump(existing_content, f, ensure_ascii=False)

            total_chapters = len(chapters)
            completed_chapters = 0

            # Create CLI progress bar
            with tqdm(total=total_chapters, desc='下载进度') as pbar:
                # Download chapters
                content = existing_content.copy()  # Start with existing content including metadata
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.xc) as executor:
                    future_to_chapter = {
                        executor.submit(
                            self._download_chapter,
                            title,
                            chapter_id,
                            existing_content
                        ): title
                        for title, chapter_id in chapters.items()
                    }

                    for future in concurrent.futures.as_completed(future_to_chapter):
                        chapter_title = future_to_chapter[future]
                        try:
                            chapter_content = future.result()
                            if chapter_content:
                                content[chapter_title] = chapter_content
                                # Save progress periodically
                                if completed_chapters % 5 == 0:
                                    with open(self.book_json_path, 'w', encoding='UTF-8') as f:
                                        json.dump(content, f, ensure_ascii=False)
                        except Exception as e:
                            self.log_callback(f'下载章节失败 {chapter_title}: {str(e)}')

                        completed_chapters += 1
                        pbar.update(1)
                        self.progress_callback(
                            completed_chapters,
                            total_chapters,
                            '下载进度',
                            chapter_title
                        )

                # Save final content
                with open(self.book_json_path, 'w', encoding='UTF-8') as f:
                    json.dump(content, f, ensure_ascii=False)

                # Generate output file
                if self.config.save_mode == SaveMode.SINGLE_TXT:
                    return self._save_single_txt(safe_name, content)
                else:
                    return self._save_split_txt(safe_name, content)

        finally:
            # Send 100% completion if not already sent
            if 'completed_chapters' in locals() and 'total_chapters' in locals():
                if completed_chapters < total_chapters:
                    self.progress_callback(total_chapters, total_chapters, '下载完成')

    def _download_epub(self, novel_id: int) -> str:
        """Download novel in EPUB format"""
        try:
            name, chapters, status = self._get_chapter_list(novel_id)
            if name == 'err':
                return 'err'

            safe_name = self._sanitize_filename(name)
            self.log_callback(f'\n开始下载《{name}》，状态：{status[0]}')

            # Create EPUB book
            book = epub.EpubBook()
            book.set_title(name)
            book.set_language('zh')

            # Get author info and cover
            author = self._get_author_info(novel_id)
            if author:
                book.add_author(author)
            cover_url = self._get_cover_url(novel_id)
            if cover_url:
                self._add_cover_to_epub(book, cover_url)

            total_chapters = len(chapters)
            completed_chapters = 0

            # Download chapters with progress tracking
            epub_chapters = []
            with tqdm(total=total_chapters, desc='下载进度') as pbar:
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.xc) as executor:
                    future_to_chapter = {
                        executor.submit(
                            self._download_chapter_for_epub,
                            title,
                            chapter_id
                        ): title
                        for title, chapter_id in chapters.items()
                    }

                    for future in concurrent.futures.as_completed(future_to_chapter):
                        chapter_title = future_to_chapter[future]
                        try:
                            epub_chapter = future.result()
                            if epub_chapter:
                                epub_chapters.append((chapter_title, epub_chapter))
                        except Exception as e:
                            self.log_callback(f'下载章节失败 {chapter_title}: {str(e)}')

                        completed_chapters += 1
                        pbar.update(1)
                        self.progress_callback(
                            completed_chapters,
                            total_chapters,
                            '下载进度',
                            chapter_title
                        )

            # Sort chapters by their original order
            epub_chapters.sort(key=lambda x: list(chapters.keys()).index(x[0]))
            for _, chapter in epub_chapters:
                book.add_item(chapter)

            # Add navigation
            book.toc = [chapter for _, chapter in epub_chapters]
            book.spine = ['nav'] + [chapter for _, chapter in epub_chapters]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())

            # Save EPUB file
            epub_path = os.path.join(self.config.save_path, f'{safe_name}.epub')
            epub.write_epub(epub_path, book)
            return 's'

        finally:
            if 'completed_chapters' in locals() and 'total_chapters' in locals():
                if completed_chapters < total_chapters:
                    self.progress_callback(total_chapters, total_chapters, '下载完成')

    def _download_chapter(self, title: str, chapter_id: str, existing_content: Dict) -> Optional[str]:
        """Download a single chapter with retries and intelligent error handling"""
        if title in existing_content:
            self.zj[title] = existing_content[title]
            return existing_content[title]

        self.log_callback(f'下载章节: {title}')
        retries = self.config.retry_count
        last_error = None
        
        # 详细记录重试过程
        self._write_debug_log(f"🔄 开始下载章节「{title}」(ID: {chapter_id}) - 最大重试次数: {retries}")
        self._write_debug_log(f"📋 重试间隔配置: {self.config.retry_delays}")

        while retries > 0:
            try:
                self._write_debug_log(f"📡 尝试下载章节「{title}」- 剩余重试次数: {retries}")
                
                content = self._download_chapter_content(chapter_id)
                
                # 统一处理各种失败情况
                if content == 'err' or not content or not content.strip():
                    self.tcs += 1
                    
                    if content == 'err':
                        error_msg = "API返回错误"
                    elif not content:
                        error_msg = "返回内容为None"
                    else:
                        error_msg = "返回内容为空字符串"
                    
                    # 更新反爬检测统计
                    self.empty_content_count += 1
                    self.total_empty_count += 1
                    
                    # 检测反爬情况并调整策略
                    if self.empty_content_count >= 3:
                        self.adaptive_delay_multiplier = min(5.0, self.adaptive_delay_multiplier + 0.5)
                        self._write_debug_log(f"🚨 连续失败 {self.empty_content_count} 次，疑似反爬检测！")
                        self._write_debug_log(f"📊 调整延时倍数至: {self.adaptive_delay_multiplier:.1f}")
                        self.log_callback(f"🚨 检测到连续失败，已调整下载策略")
                    
                    # 记录详细的失败信息
                    time_since_success = time.time() - self.last_successful_time
                    self._write_debug_log(f"⚠️ 章节「{title}」下载异常: {error_msg}")
                    self._write_debug_log(f"📊 失败统计 - 连续: {self.empty_content_count}, 总计: {self.total_empty_count}")
                    self._write_debug_log(f"⏰ 距离上次成功: {time_since_success:.1f}秒")
                    
                    # Cookie 刷新机制
                    if self.tcs > 7:
                        self.tcs = 0
                        self._write_debug_log(f"🔄 触发Cookie刷新 (chapter_id: {chapter_id})")
                        self._get_new_cookie(self.tzj)
                        self.log_callback(f"🔄 检测到多次失败，已刷新Cookie")
                    
                    raise Exception(f"Chapter download failed: {error_msg}")

                # 成功时更新统计信息
                self.empty_content_count = 0  # 重置连续空内容计数
                self.last_successful_time = time.time()
                
                # 🔄 策略2：增加成功下载计数器
                self.successful_downloads += 1
                
                # 🔄 策略2：检查是否需要主动刷新Cookie（每20个章节）
                if self._should_refresh_cookie_proactively():
                    effective_chapter_id = int(chapter_id) if chapter_id else (self.tzj if self.tzj else 1)
                    self._write_debug_log(f"🔄 策略2：第{self.successful_downloads}个章节，主动刷新Cookie (chapter_id: {effective_chapter_id})")
                    self._get_new_cookie(effective_chapter_id)
                    self.log_callback(f"🔄 策略2：已下载{self.successful_downloads}个章节，主动刷新Cookie（每20章节策略）")
                
                # 根据成功情况调整延时倍数
                if self.adaptive_delay_multiplier > 1.0:
                    self.adaptive_delay_multiplier = max(1.0, self.adaptive_delay_multiplier - 0.1)
                    self._write_debug_log(f"📈 下载成功，降低延时倍数至: {self.adaptive_delay_multiplier:.1f}")
                
                # 🎭 策略3：模拟真实阅读行为
                self._smart_reading_pause(title)
                
                # 自适应延时
                base_delay_ms = random.randint(self.config.delay[0], self.config.delay[1])
                actual_delay_ms = int(base_delay_ms * self.adaptive_delay_multiplier)
                self._write_debug_log(f"⏱️ 章节「{title}」下载成功，延时 {actual_delay_ms}ms (基础:{base_delay_ms}ms × 倍数:{self.adaptive_delay_multiplier:.1f})")
                time.sleep(actual_delay_ms / 1000)

                # Save progress periodically
                self.cs += 1
                if self.cs >= 5:
                    self.cs = 0
                    self._save_progress(title, content)

                self.zj[title] = content
                self._write_debug_log(f"✅ 章节「{title}」下载完成，内容长度: {len(content)} 字符")
                return content

            except Exception as e:
                last_error = e
                retries -= 1
                
                self._write_debug_log(f"❌ 章节「{title}」重试失败: {str(e)} (剩余重试: {retries})")
                
                if retries > 0:
                    # 使用配置文件中的重试间隔
                    attempt_index = self.config.retry_count - retries
                    if attempt_index < len(self.config.retry_delays):
                        retry_delay = self.config.retry_delays[attempt_index]
                    else:
                        # 如果重试次数超过配置的间隔数组，使用最后一个值
                        retry_delay = self.config.retry_delays[-1]
                    
                    # 🚨 用户要求：明确失败原因
                    failure_reason = self._get_failure_reason(e)
                    
                    # 🚨 策略2：更激进的Cookie刷新检查（失败1次就刷新）
                    cookie_action = ""
                    if self.tcs > 0:  # 策略2：失败1次就尝试刷新Cookie
                        self.tcs = 0
                        # 修复Cookie刷新：使用有效的chapter_id
                        effective_chapter_id = int(chapter_id) if chapter_id else (self.tzj if self.tzj else 1)
                        self._write_debug_log(f"🔄 策略2：失败1次即刷新Cookie (effective_chapter_id: {effective_chapter_id})")
                        self._get_new_cookie(effective_chapter_id)
                        cookie_action = " (策略2: 已刷新Cookie)"
                    
                    self._write_debug_log(f"⏳ 等待 {retry_delay}s 后重试... (重试间隔配置索引: {attempt_index})")
                    
                    # 🚨 用户要求：包含具体失败原因的重试日志
                    self.log_callback(f"⚠️ 章节「{title}」下载失败 ({failure_reason})，{retry_delay}s后重试 (剩余{retries}次){cookie_action}")
                    
                    # 必要时输出完整响应
                    if "内容为空" not in failure_reason and "网络" not in failure_reason:
                        self._write_debug_log(f"📥 重试前获取完整响应内容:")
                        try:
                            debug_content = self._download_chapter_content(int(chapter_id), test_mode=True)
                            self._write_debug_log(f"📥 完整响应: {repr(debug_content[:1000])}{'...' if len(debug_content) > 1000 else ''}")
                        except:
                            self._write_debug_log(f"📥 无法获取响应内容")
                    
                    time.sleep(retry_delay)
                else:
                    self._write_debug_log(f"💥 章节「{title}」最终下载失败: {str(e)}")
                    self.log_callback(f'下载失败 {title}: {str(e)}')

        if last_error:
            raise last_error
        return None

    def _download_chapter_for_epub(self, title: str, chapter_id: str) -> Optional[epub.EpubHtml]:
        """Download and format chapter for EPUB"""
        content = self._download_chapter(title, chapter_id, {})
        if not content:
            return None

        chapter = epub.EpubHtml(
            title=title,
            file_name=f'chapter_{chapter_id}.xhtml',
            lang='zh'
        )

        # 使用<p>标签包裹每个段落，确保没有多余的换行符
        formatted_content = ''.join(f'<p>{para.strip()}</p>' for para in content.split('\n') if para.strip())
        chapter.content = f'<h1>{title}</h1>{formatted_content}'
        return chapter

    def _save_single_txt(self, name: str, content: dict) -> str:
        """Save all chapters to a single TXT file"""
        output_path = os.path.join(self.download_dir, f'{name}.txt')  # 保存到下载目录
        fg = '\n' + self.config.kgf * self.config.kg

        with open(output_path, 'w', encoding='UTF-8') as f:
            for title, chapter_content in content.items():
                # 跳过元数据项
                if title.startswith('_'):
                    continue
                    
                f.write(f'\n{title}{fg}')
                if self.config.kg == 0:
                    f.write(f'{chapter_content}\n')
                else:
                    # 将替换结果存储在一个变量中
                    modified_content = chapter_content.replace("\n", fg)
                    # 在 f-string 中使用这个变量
                    f.write(f'{modified_content}\n')
        
        return 's'  # 返回成功标识

    def _save_single_txt_to_folder(self, name: str, content: dict, output_dir: str) -> str:
        """Save all chapters to a single TXT file in specified folder with smart chapter ordering"""
        output_path = os.path.join(output_dir, f'{name}.txt')
        fg = '\n' + self.config.kgf * self.config.kg

        # 提取所有章节及其编号，跳过元数据
        chapters_with_numbers = []
        for title, chapter_content in content.items():
            if title.startswith('_'):
                continue
            chapter_num = self._extract_chapter_number(title)
            chapters_with_numbers.append((chapter_num, title, chapter_content))
        
        # 按章节编号排序
        chapters_with_numbers.sort(key=lambda x: x[0])
        
        self.log_callback(f'按顺序合并章节: 共 {len(chapters_with_numbers)} 章')
        
        with open(output_path, 'w', encoding='UTF-8') as f:
            if not chapters_with_numbers:
                f.write('暂无章节内容\n')
                return 's'
            
            # 获取章节编号范围
            min_chapter = chapters_with_numbers[0][0]
            max_chapter = chapters_with_numbers[-1][0]
            
            # 创建章节字典以便快速查找
            chapter_dict = {num: (title, content) for num, title, content in chapters_with_numbers}
            
            # 按顺序写入章节，处理缺失章节
            for chapter_num in range(min_chapter, max_chapter + 1):
                if chapter_num in chapter_dict:
                    title, chapter_content = chapter_dict[chapter_num]
                    f.write(f'\n{title}{fg}')
                    if self.config.kg == 0:
                        f.write(f'{chapter_content}\n')
                    else:
                        modified_content = chapter_content.replace("\n", fg)
                        f.write(f'{modified_content}\n')
                else:
                    # 处理缺失章节
                    missing_title = f'第 {chapter_num} 章 当前章节缺失'
                    f.write(f'\n{missing_title}{fg}')
                    f.write(f'抱歉，当前章节下载失败或暂不可用\n')
                    self.log_callback(f'⚠️ 检测到缺失章节: 第 {chapter_num} 章')
        
        return 's'  # 返回成功标识

    def _save_split_txt_to_folder(self, name: str, content: Dict, output_dir: str) -> str:
        """Save each chapter to a separate TXT file in specified folder"""
        chapter_output_dir = os.path.join(output_dir, name)
        os.makedirs(chapter_output_dir, exist_ok=True)

        for title, chapter_content in content.items():
            # 跳过元数据项
            if title.startswith('_'):
                continue
                
            chapter_path = os.path.join(
                chapter_output_dir,
                f'{self._sanitize_filename(title)}.txt'
            )
            if self.config.kg == 0:
                replacement_content = chapter_content
            else:
                replacement_content = chapter_content.replace("\n", self.config.kgf * self.config.kg)

            with open(chapter_path, 'w', encoding='UTF-8') as f:
                f.write(f'{replacement_content}\n')

        return 's'

    def _save_split_txt(self, name: str, content: Dict) -> str:
        """Save each chapter to a separate TXT file"""
        output_dir = os.path.join(self.download_dir, name)  # 保存到下载目录
        os.makedirs(output_dir, exist_ok=True)

        for title, chapter_content in content.items():
            chapter_path = os.path.join(
                output_dir,
                f'{self._sanitize_filename(title)}.txt'
            )
            if self.config.kg == 0:
                replacement_content = chapter_content
            else:
                replacement_content = chapter_content.replace("\n", self.config.kgf * self.config.kg)

            with open(chapter_path, 'w', encoding='UTF-8') as f:
                f.write(f'{replacement_content}\n')

        return 's'

    def update_all_novels(self):
        """Update all novels in records"""
        if not os.path.exists(self.record_path):
            self.log_callback("No novels to update")
            return

        with open(self.record_path, 'r', encoding='UTF-8') as f:
            novels = json.load(f)

        for novel_id in novels:
            self.log_callback(f"Updating novel {novel_id}")
            status = self.download_novel(novel_id)
            if not status:
                novels.remove(novel_id)

        with open(self.record_path, 'w', encoding='UTF-8') as f:
            json.dump(novels, f)

    def _download_html(self, novel_id: int) -> str:
        """Download novel in HTML format"""
        try:
            name, chapters, status = self._get_chapter_list(novel_id)
            if name == 'err':
                return 'err'

            safe_name = self._sanitize_filename(name)
            html_dir = os.path.join(self.config.save_path, f"{safe_name}(html)")
            os.makedirs(html_dir, exist_ok=True)

            self.log_callback(f'\n开始下载《{name}》，状态：{status[0]}')

            # Create index.html
            toc_content = self._create_html_index(name, chapters)
            with open(os.path.join(html_dir, "index.html"), "w", encoding='UTF-8') as f:
                f.write(toc_content)

            total_chapters = len(chapters)
            completed_chapters = 0

            # Download chapters with progress tracking
            with tqdm(total=total_chapters, desc='下载进度') as pbar:
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.xc) as executor:
                    future_to_chapter = {
                        executor.submit(
                            self._download_chapter_for_html,
                            title,
                            chapter_id,
                            html_dir,
                            list(chapters.keys())
                        ): title
                        for title, chapter_id in chapters.items()
                    }

                    for future in concurrent.futures.as_completed(future_to_chapter):
                        chapter_title = future_to_chapter[future]
                        try:
                            future.result()
                        except Exception as e:
                            self.log_callback(f'下载章节失败 {chapter_title}: {str(e)}')

                        completed_chapters += 1
                        pbar.update(1)
                        self.progress_callback(
                            completed_chapters,
                            total_chapters,
                            '下载进度',
                            chapter_title
                        )

            return 's'

        finally:
            if 'completed_chapters' in locals() and 'total_chapters' in locals():
                if completed_chapters < total_chapters:
                    self.progress_callback(total_chapters, total_chapters, '下载完成')

    def _download_latex(self, novel_id: int) -> str:
        """Download novel in LaTeX format"""
        try:
            name, chapters, status = self._get_chapter_list(novel_id)
            if name == 'err':
                return 'err'

            safe_name = self._sanitize_filename(name)
            self.log_callback(f'\n开始下载《{name}》，状态：{status[0]}')

            # Create LaTeX document header
            latex_content = self._create_latex_header(name)

            total_chapters = len(chapters)
            completed_chapters = 0
            chapter_contents = []

            # Download chapters with progress tracking
            with tqdm(total=total_chapters, desc='下载进度') as pbar:
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.xc) as executor:
                    future_to_chapter = {
                        executor.submit(
                            self._download_chapter_for_latex,
                            title,
                            chapter_id
                        ): title
                        for title, chapter_id in chapters.items()
                    }

                    for future in concurrent.futures.as_completed(future_to_chapter):
                        chapter_title = future_to_chapter[future]
                        try:
                            chapter_content = future.result()
                            if chapter_content:
                                chapter_contents.append((chapter_title, chapter_content))
                        except Exception as e:
                            self.log_callback(f'下载章节失败 {chapter_title}: {str(e)}')

                        completed_chapters += 1
                        pbar.update(1)
                        self.progress_callback(
                            completed_chapters,
                            total_chapters,
                            '下载进度',
                            chapter_title
                        )

            # Sort chapters and add to document
            chapter_contents.sort(key=lambda x: list(chapters.keys()).index(x[0]))
            for title, content in chapter_contents:
                latex_content += self._format_latex_chapter(title, content)

            # Add document footer and save
            latex_content += "\n\\end{document}"
            latex_path = os.path.join(self.config.save_path, f'{safe_name}.tex')
            with open(latex_path, 'w', encoding='UTF-8') as f:
                f.write(latex_content)

            return 's'

        finally:
            if 'completed_chapters' in locals() and 'total_chapters' in locals():
                if completed_chapters < total_chapters:
                    self.progress_callback(total_chapters, total_chapters, '下载完成')

    def _create_html_index(self, title: str, chapters: Dict[str, str]) -> str:
        """Create HTML index page with CSS styling"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 目录</title>
    <style>
        :root {{
            --bg-color: #f5f5f5;
            --text-color: #333;
            --link-color: #007bff;
            --hover-color: #0056b3;
        }}
        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg-color: #222;
                --text-color: #fff;
                --link-color: #66b0ff;
                --hover-color: #99ccff;
            }}
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: var(--bg-color);
            color: var(--text-color);
        }}
        h1 {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .toc {{
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
        }}
        .toc a {{
            color: var(--link-color);
            text-decoration: none;
            display: block;
            padding: 8px 0;
            transition: all 0.2s;
        }}
        .toc a:hover {{
            color: var(--hover-color);
            transform: translateX(10px);
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="toc">
        {''.join(f'<a href="{self._sanitize_filename(title)}.html">{title}</a>' for title in chapters.keys())}
    </div>
</body>
</html>
"""

    def _create_latex_header(self, title: str) -> str:
        """Create LaTeX document header"""
        return f"""\\documentclass[12pt,a4paper]{{article}}
\\usepackage{{ctex}}
\\usepackage{{geometry}}
\\usepackage{{hyperref}}
\\usepackage{{bookmark}}

\\geometry{{
    top=2.54cm,
    bottom=2.54cm,
    left=3.18cm,
    right=3.18cm
}}

\\title{{{title}}}
\\author{{Generated by NovelDownloader}}
\\date{{\\today}}

\\begin{{document}}
\\maketitle
\\tableofcontents
\\newpage
"""

    def _download_chapter_for_html(self, title: str, chapter_id: str, output_dir: str, all_titles: List[str]) -> None:
        """Download and format chapter for HTML"""
        content = self._download_chapter(title, chapter_id, {})
        if not content:
            return

        current_index = all_titles.index(title)
        prev_link = f'<a href="{self._sanitize_filename(all_titles[current_index - 1])}.html">上一章</a>' if current_index > 0 else ''
        next_link = f'<a href="{self._sanitize_filename(all_titles[current_index + 1])}.html">下一章</a>' if current_index < len(
            all_titles) - 1 else ''

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        /* ... Same CSS variables as index ... */
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.8;
            margin: 0;
            padding: 20px;
            background-color: var(--bg-color);
            color: var(--text-color);
            max-width: 800px;
            margin: 0 auto;
        }}
        .navigation {{
            display: flex;
            justify-content: space-between;
            padding: 20px 0;
            position: sticky;
            top: 0;
            background-color: var(--bg-color);
        }}
        .navigation a {{
            color: var(--link-color);
            text-decoration: none;
            padding: 8px 16px;
            border: 1px solid var(--link-color);
            border-radius: 4px;
        }}
        .content {{
            text-indent: 2em;
            margin-bottom: 40px;
        }}
    </style>
</head>
<body>
    <div class="navigation">
        <a href="index.html">目录</a>
        {prev_link}
        {next_link}
    </div>
    <h1>{title}</h1>
    <div class="content">
        {content.replace(chr(10), '<br>' + self.config.kgf * self.config.kg)}
    </div>
    <div class="navigation">
        <a href="index.html">目录</a>
        {prev_link}
        {next_link}
    </div>
</body>
</html>
"""

        with open(os.path.join(output_dir, f"{self._sanitize_filename(title)}.html"), "w", encoding='UTF-8') as f:
            f.write(html_content)

    def _download_chapter_for_latex(self, title: str, chapter_id: str) -> Optional[str]:
        """Download and format chapter for LaTeX"""
        content = self._download_chapter(title, chapter_id, {})
        if not content:
            return None
        return self._format_latex_chapter(title, content)

    def _format_latex_chapter(self, title: str, content: str) -> str:
        """Format chapter content for LaTeX"""
        # Escape special LaTeX characters
        special_chars = ['\\', '{', '}', '&', '#', '$', '^', '_', '~', '%']
        for char in special_chars:
            content = content.replace(char, f'\\{char}')
            title = title.replace(char, f'\\{char}')

        # Format content with proper spacing
        content = content.replace('\n', '\n\n' + self.config.kgf * self.config.kg)

        return f"""
\\section{{{title}}}
{content}
"""

    def _test_cookie(self, chapter_id: int, cookie: str) -> str:
        """Test if cookie is valid"""
        self.cookie = cookie
        if len(self._download_chapter_content(chapter_id, test_mode=True)) > 200:
            return 's'
        return 'err'

    def _get_chapter_list(self, novel_id: int) -> tuple:
        """Get novel info and chapter list with detailed logging"""
        url = f'https://fanqienovel.com/page/{novel_id}'
        
        # 详细记录请求信息
        self._write_debug_log(f"🌐 请求章节列表: {url}")
        self._write_debug_log(f"🔑 使用Cookie: {self.cookie}")
        
        response = req.get(url, headers=self.headers)
        self._write_debug_log(f"📡 响应状态码: {response.status_code}")
        self._write_debug_log(f"📏 响应内容长度: {len(response.text)} 字符")
        
        ele = etree.HTML(response.text)

        chapters = {}
        a_elements = ele.xpath('//div[@class="chapter"]/div/a')
        self._write_debug_log(f"📚 找到章节元素数量: {len(a_elements)}")
        
        if not a_elements:
            self._write_debug_log("❌ 未找到任何章节元素，可能是页面结构变化或访问受限")
            return 'err', {}, []

        null_title_count = 0
        valid_chapters = 0
        
        for i, a in enumerate(a_elements):
            href = a.xpath('@href')
            if not href:
                self._write_debug_log(f"⚠️ 第{i+1}个章节元素缺少href属性")
                continue
                
            chapter_title = a.text
            chapter_id = href[0].split('/')[-1]
            
            # 详细记录每个章节的信息
            if not chapter_title or not chapter_title.strip():
                null_title_count += 1
                self._write_debug_log(f"🚨 第{i+1}个章节标题为空! 章节ID: {chapter_id}")
                self._write_debug_log(f"   - 元素HTML: {etree.tostring(a, encoding='unicode')[:200]}")
                # 不生成假标题，保留问题让用户知道
                continue
            else:
                chapters[chapter_title.strip()] = chapter_id
                valid_chapters += 1
                if i < 5 or i % 100 == 0:  # 记录前5个和每100个章节
                    self._write_debug_log(f"✅ 章节{i+1}: 「{chapter_title.strip()}」-> ID: {chapter_id}")

        self._write_debug_log(f"📊 章节统计: 有效章节 {valid_chapters} 个，空标题章节 {null_title_count} 个")
        
        if null_title_count > 0:
            self.log_callback(f"⚠️ 发现 {null_title_count} 个空标题章节，这些章节将被跳过")
            self.log_callback(f"💡 建议检查网络连接或稍后重试，也可能是网站反爬虫机制")

        title = ele.xpath('//h1/text()')
        status = ele.xpath('//span[@class="info-label-yellow"]/text()')
        
        self._write_debug_log(f"📖 小说标题: {title[0] if title else '未找到'}")
        self._write_debug_log(f"📊 小说状态: {status[0] if status else '未找到'}")

        if not title or not status:
            self._write_debug_log("❌ 无法获取小说基本信息（标题或状态）")
            return 'err', {}, []

        return title[0], chapters, status

    def _download_chapter_content(self, chapter_id: int, test_mode: bool = False) -> str:
        """Download content with fallback and enhanced error handling"""
        # 🎭 策略3：使用随机化的真实请求头
        headers = self._get_randomized_headers()
        headers['cookie'] = self.cookie

        for attempt in range(3):
            try:
                self._write_debug_log(f"📡 尝试方法1: 标准API (章节ID: {chapter_id}, 尝试: {attempt + 1}/3)")
                
                # Try primary method
                response = req.get(
                    f'https://fanqienovel.com/reader/{chapter_id}',
                    headers=headers,
                    timeout=10
                )
                response.raise_for_status()
                
                self._write_debug_log(f"📥 API响应状态: {response.status_code}, 内容长度: {len(response.text)}")

                content = '\n'.join(
                    etree.HTML(response.text).xpath(
                        '//div[@class="muye-reader-content noselect"]//p/text()'
                    )
                )
                
                self._write_debug_log(f"📝 XPath提取结果长度: {len(content)} 字符")

                if test_mode:
                    return content

                # 检查内容是否有效
                if not content or len(content.strip()) < 10:
                    self._write_debug_log(f"⚠️ 方法1内容过短或为空: {repr(content[:100])}")
                    raise Exception(f"Content too short or empty (length: {len(content)})")

                try:
                    decoded = self._decode_content(content)
                    self._write_debug_log(f"✅ 内容解码成功，最终长度: {len(decoded)} 字符")
                    return decoded
                except Exception as decode_err:
                    self._write_debug_log(f"⚠️ 解码模式0失败: {str(decode_err)}")
                    # Try alternative decoding mode
                    try:
                        decoded = self._decode_content(content, mode=1)
                        self._write_debug_log(f"✅ 解码模式1成功，最终长度: {len(decoded)} 字符")
                        return decoded
                    except Exception as decode_err2:
                        self._write_debug_log(f"⚠️ 解码模式1失败: {str(decode_err2)}")
                        # Fallback HTML processing
                        self._write_debug_log(f"🔄 使用后备HTML处理")
                        content = content[6:]
                        tmp = 1
                        result = ''
                        for i in content:
                            if i == '<':
                                tmp += 1
                            elif i == '>':
                                tmp -= 1
                            elif tmp == 0:
                                result += i
                            elif tmp == 1 and i == 'p':
                                result = (result + '\n').replace('\n\n', '\n')
                        
                        if result and len(result.strip()) > 10:
                            self._write_debug_log(f"✅ 后备处理成功，最终长度: {len(result)} 字符")
                            return result
                        else:
                            raise Exception(f"Fallback processing failed, result too short: {len(result)}")

            except Exception as e:
                self._write_debug_log(f"❌ 方法1失败: {str(e)}")
                
                # Try alternative API endpoint
                try:
                    self._write_debug_log(f"🔄 尝试方法2: 备用API (章节ID: {chapter_id})")
                    
                    response = req.get(
                        f'https://fanqienovel.com/api/reader/full?itemId={chapter_id}',
                        headers=headers,
                        timeout=10
                    )
                    response.raise_for_status()
                    
                    self._write_debug_log(f"📥 备用API响应状态: {response.status_code}")
                    
                    data = json.loads(response.text)
                    content = data['data']['chapterData']['content']
                    
                    self._write_debug_log(f"📝 备用API内容长度: {len(content)} 字符")

                    if test_mode:
                        return content
                    
                    # 检查内容是否有效
                    if not content or len(content.strip()) < 10:
                        self._write_debug_log(f"⚠️ 方法2内容过短或为空: {repr(content[:100])}")
                        raise Exception(f"Backup API content too short (length: {len(content)})")

                    decoded = self._decode_content(content)
                    self._write_debug_log(f"✅ 备用API解码成功，最终长度: {len(decoded)} 字符")
                    return decoded
                    
                except Exception as backup_err:
                    self._write_debug_log(f"❌ 方法2也失败: {str(backup_err)}")
                    
                    if attempt == 2:  # Last attempt
                        self._write_debug_log(f"💥 所有方法均失败，章节ID: {chapter_id}")
                        if test_mode:
                            return 'err'
                        raise Exception(f"All download methods failed. Primary: {str(e)}, Backup: {str(backup_err)}")
                    
                    self._write_debug_log(f"⏳ 等待1秒后重试...")
                    time.sleep(1)

    def _get_author_info(self, novel_id: int) -> Optional[str]:
        """Get author information from novel page"""
        url = f'https://fanqienovel.com/page/{novel_id}'
        try:
            response = req.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            script_tag = soup.find('script', type="application/ld+json")
            if script_tag:
                data = json.loads(script_tag.string)
                if 'author' in data:
                    return data['author'][0]['name']
        except Exception as e:
            self.log_callback(f"获取作者信息失败: {str(e)}")
        return None

    def _get_cover_url(self, novel_id: int) -> Optional[str]:
        """Get cover image URL from novel page"""
        url = f'https://fanqienovel.com/page/{novel_id}'
        try:
            response = req.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            script_tag = soup.find('script', type="application/ld+json")
            if script_tag:
                data = json.loads(script_tag.string)
                if 'image' in data:
                    return data['image'][0]
        except Exception as e:
            self.log_callback(f"获取封面图片失败: {str(e)}")
        return None

    def _add_cover_to_epub(self, book: epub.EpubBook, cover_url: str):
        """Add cover image to EPUB book"""
        try:
            response = req.get(cover_url)
            if response.status_code == 200:
                book.set_cover('cover.jpg', response.content)

                # Add cover page
                cover_content = f'''
                    <div style="text-align: center; padding: 0; margin: 0;">
                        <img src="cover.jpg" alt="Cover" style="max-width: 100%; height: auto;"/>
                    </div>
                '''
                cover_page = epub.EpubHtml(
                    title='Cover',
                    file_name='cover.xhtml',
                    content=cover_content,
                    media_type='image/jpeg'
                )
                book.add_item(cover_page)
                book.spine.insert(0, cover_page)
        except Exception as e:
            self.log_callback(f"添加封面失败: {str(e)}")

    def _extract_chapter_number(self, title: str) -> int:
        """Extract chapter number from title for sorting"""
        # 尝试提取章节编号的多种模式
        patterns = [
            r'第\s*(\d+)\s*章',      # 第1章, 第 1 章
            r'第\s*([一二三四五六七八九十百千万]+)\s*章',  # 第一章, 第二十章
            r'章节?\s*(\d+)',        # 章节1, 章1  
            r'(\d+)\s*章',           # 1章
            r'Chapter\s*(\d+)',      # Chapter 1
            r'Ch\s*(\d+)',           # Ch 1
            r'^(\d+)',               # 开头的数字
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                chapter_num_str = match.group(1)
                
                # 处理中文数字
                if chapter_num_str in ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']:
                    chinese_numbers = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, 
                                     '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
                    return chinese_numbers.get(chapter_num_str, 0)
                
                # 处理阿拉伯数字
                try:
                    return int(chapter_num_str)
                except ValueError:
                    continue
        
        # 如果没有找到章节编号，返回0（将排在最前面）
        return 0

    def _get_failure_reason(self, exception: Exception) -> str:
        """根据异常类型返回用户友好的失败原因"""
        error_str = str(exception).lower()
        
        if "chapter download failed" in error_str:
            if "api返回错误" in error_str:
                return "API返回错误"
            elif "返回内容为none" in error_str:
                return "响应内容为空(None)"
            elif "返回内容为空字符串" in error_str:
                return "响应内容为空字符串"
            else:
                return "内容获取失败"
        elif "timeout" in error_str or "timed out" in error_str:
            return "网络超时"
        elif "connection" in error_str:
            return "网络连接错误"
        elif "404" in error_str:
            return "章节不存在(404)"
        elif "403" in error_str:
            return "访问被拒绝(403)"
        elif "500" in error_str:
            return "服务器错误(500)"
        elif "nonetype" in error_str and "pathlike" in error_str:
            return "文件路径错误(变量为None)"
        elif "decode" in error_str or "encoding" in error_str:
            return "内容解码错误"
        elif "json" in error_str:
            return "JSON解析错误"
        else:
            # 🚨 用户要求：不要截断错误信息，显示完整内容
            return f"未知错误: {str(exception)}"

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for different platforms with enhanced debugging"""
        self._write_debug_log(f"🔧 _sanitize_filename调用 - 输入: {repr(filename)} (类型: {type(filename).__name__})")
        
        # 处理None或空值的情况
        if filename is None:
            self._write_debug_log(f"❌ _sanitize_filename: 输入为None!")
            result = "ERROR_None_filename"
            self._write_debug_log(f"🔧 _sanitize_filename返回: {repr(result)}")
            return result
        
        if not filename:
            self._write_debug_log(f"❌ _sanitize_filename: 输入为空字符串!")
            result = "ERROR_Empty_filename"
            self._write_debug_log(f"🔧 _sanitize_filename返回: {repr(result)}")
            return result
        
        # 确保输入是字符串类型
        if not isinstance(filename, str):
            self._write_debug_log(f"❌ _sanitize_filename: 输入不是字符串类型: {type(filename)}")
            filename_str = str(filename)
            self._write_debug_log(f"🔄 转换为字符串: {repr(filename_str)}")
            filename = filename_str
        
        original_filename = filename
        illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        illegal_chars_rep = ['＜', '＞', '：', '＂', '／', '＼', '｜', '？', '＊']
        
        for old, new in zip(illegal_chars, illegal_chars_rep):
            if old in filename:
                self._write_debug_log(f"🔄 替换字符: '{old}' -> '{new}'")
                filename = filename.replace(old, new)
        
        self._write_debug_log(f"🔧 _sanitize_filename完成 - 原始: {repr(original_filename)} -> 结果: {repr(filename)}")
        return filename

    def _parse_novel_id(self, novel_id: Union[str, int]) -> Optional[int]:
        """Parse novel ID from input (URL or ID)"""
        if isinstance(novel_id, str) and novel_id.startswith('http'):
            novel_id = novel_id.split('?')[0].split('/')[-1]
        try:
            return int(novel_id)
        except ValueError:
            self.log_callback(f'Invalid novel ID: {novel_id}')
            return None

    def get_downloaded_novels(self) -> List[Dict[str, str]]:
        """Get list of downloaded novels with their paths"""
        novels = []
        for filename in os.listdir(self.bookstore_dir):
            if filename.endswith('.json'):
                novel_name = filename[:-5]  # Remove .json extension
                json_path = os.path.join(self.bookstore_dir, filename)

                try:
                    with open(json_path, 'r', encoding='UTF-8') as f:
                        novel_data = json.load(f)
                        metadata = novel_data.get('_metadata', {})

                        novels.append({
                            'name': novel_name,
                            'novel_id': metadata.get('novel_id'),
                            'status': metadata.get('status'),
                            'last_updated': metadata.get('last_updated'),
                            'json_path': json_path,
                            'txt_path': os.path.join(self.config.save_path, f'{novel_name}.txt'),
                            'epub_path': os.path.join(self.config.save_path, f'{novel_name}.epub'),
                            'html_path': os.path.join(self.config.save_path, f'{novel_name}(html)'),
                            'latex_path': os.path.join(self.config.save_path, f'{novel_name}.tex')
                        })
                except Exception as e:
                    self.log_callback(f"Error reading novel data for {novel_name}: {str(e)}")
                    # Add novel with minimal info if metadata can't be read
                    novels.append({
                        'name': novel_name,
                        'novel_id': None,
                        'status': None,
                        'last_updated': None,
                        'json_path': json_path,
                        'txt_path': os.path.join(self.config.save_path, f'{novel_name}.txt'),
                        'epub_path': os.path.join(self.config.save_path, f'{novel_name}.epub'),
                        'html_path': os.path.join(self.config.save_path, f'{novel_name}(html)'),
                        'latex_path': os.path.join(self.config.save_path, f'{novel_name}.tex')
                    })
        return novels

    def backup_data(self, backup_dir: str):
        """Backup all data to specified directory"""
        os.makedirs(backup_dir, exist_ok=True)

        # Backup configuration
        if os.path.exists(self.config_path):
            shutil.copy2(self.config_path, os.path.join(backup_dir, 'config.json'))

        # Backup records
        if os.path.exists(self.record_path):
            shutil.copy2(self.record_path, os.path.join(backup_dir, 'record.json'))

        # Backup novels
        novels_backup_dir = os.path.join(backup_dir, 'novels')
        os.makedirs(novels_backup_dir, exist_ok=True)
        for novel in self.get_downloaded_novels():
            shutil.copy2(novel['json_path'], novels_backup_dir)

    def _decode_content(self, content: str, mode: int = 0) -> str:
        """Decode novel content using both charset modes"""
        result = ''
        for char in content:
            uni = ord(char)
            if self.CODE[mode][0] <= uni <= self.CODE[mode][1]:
                bias = uni - self.CODE[mode][0]
                if 0 <= bias < len(self.charset[mode]) and self.charset[mode][bias] != '?':
                    result += self.charset[mode][bias]
                else:
                    result += char
            else:
                result += char
        return result

    def _update_records(self, novel_id: int):
        """Update download records"""
        if os.path.exists(self.record_path):
            with open(self.record_path, 'r', encoding='UTF-8') as f:
                records = json.load(f)
        else:
            records = []

        if novel_id not in records:
            records.append(novel_id)
            with open(self.record_path, 'w', encoding='UTF-8') as f:
                json.dump(records, f)

    def _save_progress(self, title: str, content: str):
        """Save download progress"""
        self.zj[title] = content
        with open(self.book_json_path, 'w', encoding='UTF-8') as f:
            json.dump(self.zj, f, ensure_ascii=False)

    def _save_epub_from_content(self, safe_name: str, novel_content: dict, output_dir: str, novel_id: int) -> str:
        """基于已下载内容生成EPUB文件，保存到指定目录"""
        try:
            # 获取小说信息
            book = epub.EpubBook()
            book.set_identifier(str(novel_id))
            book.set_title(safe_name)
            book.set_language('zh')
            
            # 尝试获取作者信息
            try:
                author = self._get_author_info(novel_id)
                if author:
                    book.add_author(author)
                else:
                    book.add_author('未知作者')
            except:
                book.add_author('未知作者')
            
            # 添加封面（如果可以获取）
            try:
                cover_url = self._get_cover_url(novel_id)
                if cover_url:
                    self._add_cover_to_epub(book, cover_url)
            except:
                pass  # 封面获取失败不影响主要流程
            
            # 为每个章节创建EPUB章节
            for i, (title, content) in enumerate(novel_content.items()):
                if title.startswith('_'):  # 跳过元数据
                    continue
                    
                chapter = epub.EpubHtml(
                    title=title,
                    file_name=f'chapter_{i+1}.xhtml',
                    lang='zh'
                )
                
                # 格式化内容
                formatted_content = ''.join(f'<p>{para.strip()}</p>' for para in content.split('\n') if para.strip())
                chapter.content = f'<h1>{title}</h1>{formatted_content}'
                
                book.add_item(chapter)
            
            # 添加导航
            chapters = [item for item in book.get_items() if isinstance(item, epub.EpubHtml)]
            book.toc = chapters
            book.spine = ['nav'] + chapters
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            
            # 保存EPUB文件到指定目录
            epub_path = os.path.join(output_dir, f'{safe_name}.epub')
            epub.write_epub(epub_path, book)
            
            return 's'
            
        except Exception as e:
            self.log_callback(f'EPUB生成失败: {str(e)}')
            return 'err'
    
    def _save_html_from_content(self, safe_name: str, novel_content: dict, output_dir: str) -> str:
        """基于已下载内容生成HTML文件，保存到指定目录"""
        try:
            html_dir = os.path.join(output_dir, f"{safe_name}(html)")
            os.makedirs(html_dir, exist_ok=True)
            
            # 生成章节文件
            all_titles = []
            for i, (title, content) in enumerate(novel_content.items()):
                if title.startswith('_'):  # 跳过元数据
                    continue
                    
                all_titles.append(title)
                filename = f"chapter_{i+1}.html"
                chapter_path = os.path.join(html_dir, filename)
                
                # 创建HTML内容
                html_content = f"""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: serif; line-height: 1.8; margin: 40px; background: #f9f9f9; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        p {{ text-indent: 2em; margin: 1em 0; }}
        .navigation {{ margin: 20px 0; text-align: center; }}
        .navigation a {{ margin: 0 10px; padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
        .navigation a:hover {{ background: #0056b3; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="navigation">
            <a href="index.html">目录</a>
        </div>
        <h1>{title}</h1>
"""
                
                # 添加章节内容
                for paragraph in content.split('\n'):
                    if paragraph.strip():
                        html_content += f"        <p>{paragraph.strip()}</p>\n"
                
                html_content += """    </div>
</body>
</html>"""
                
                with open(chapter_path, 'w', encoding='UTF-8') as f:
                    f.write(html_content)
            
            # 生成目录文件
            index_content = self._create_html_index(safe_name, novel_content)
            index_path = os.path.join(html_dir, 'index.html')
            with open(index_path, 'w', encoding='UTF-8') as f:
                f.write(index_content)
            
            return 's'
            
        except Exception as e:
            self.log_callback(f'HTML生成失败: {str(e)}')
            return 'err'
    
    def _save_latex_from_content(self, safe_name: str, novel_content: dict, output_dir: str) -> str:
        """基于已下载内容生成LaTeX文件，保存到指定目录"""
        try:
            latex_path = os.path.join(output_dir, f'{safe_name}.tex')
            
            with open(latex_path, 'w', encoding='UTF-8') as f:
                # LaTeX文档头部
                f.write(self._create_latex_header(safe_name))
                
                # 添加章节内容
                for title, content in novel_content.items():
                    if title.startswith('_'):  # 跳过元数据
                        continue
                        
                    formatted_chapter = self._format_latex_chapter(title, content)
                    f.write(formatted_chapter)
                
                # LaTeX文档尾部
                f.write('\n\\end{document}\n')
            
            return 's'
            
        except Exception as e:
            self.log_callback(f'LaTeX生成失败: {str(e)}')
            return 'err'
    
    def _generate_pdf_from_latex(self, safe_name: str, output_dir: str) -> str:
        """使用xelatex将LaTeX文件编译为PDF"""
        try:
            import subprocess
            
            latex_file = f'{safe_name}.tex'
            latex_path = os.path.join(output_dir, latex_file)
            
            # 检查LaTeX文件是否存在
            if not os.path.exists(latex_path):
                raise Exception(f'LaTeX文件不存在: {latex_path}')
            
            # 检查xelatex是否可用
            try:
                subprocess.run(['xelatex', '--version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                raise Exception('xelatex未安装或不在PATH中。请安装LaTeX发行版（如TeX Live或MiKTeX）')
            
            # 编译LaTeX为PDF
            self.log_callback('正在使用xelatex编译PDF...')
            
            # 切换到输出目录执行xelatex，确保工作目录就是latex文件的目录
            original_cwd = os.getcwd()
            try:
                os.chdir(output_dir)
                
                # 运行xelatex，必须运行两次以正确生成目录和引用
                for i in range(2):
                    self.log_callback(f'执行第{i+1}次xelatex编译...')
                    # 修复编码问题：使用bytes模式而不是text模式
                    result = subprocess.run(
                        ['xelatex', '-interaction=nonstopmode', latex_file],
                        capture_output=True,
                        text=False,  # 使用bytes模式避免编码问题
                        timeout=300  # 5分钟超时
                    )
                    
                    if result.returncode != 0:
                        # 如果失败，尝试查看日志
                        log_file = f'{safe_name}.log'
                        error_info = f'xelatex编译失败 (返回码: {result.returncode})'
                        
                        # 获取stderr输出（如果有）
                        if result.stderr:
                            try:
                                # 尝试多种编码解码stderr
                                stderr_text = None
                                for encoding in ['utf-8', 'gbk', 'latin1']:
                                    try:
                                        stderr_text = result.stderr.decode(encoding)
                                        break
                                    except UnicodeDecodeError:
                                        continue
                                
                                if stderr_text:
                                    error_info += f'\n编译输出: {stderr_text[:500]}...'  # 限制长度
                            except:
                                error_info += '\n编译输出: <无法解码的输出>'
                        
                        # 尝试读取日志文件
                        if os.path.exists(log_file):
                            try:
                                # 尝试多种编码读取日志文件
                                log_content = None
                                for encoding in ['utf-8', 'gbk', 'latin1']:
                                    try:
                                        with open(log_file, 'r', encoding=encoding) as log_f:
                                            lines = log_f.readlines()
                                            # 取最后20行
                                            error_lines = lines[-20:] if len(lines) > 20 else lines
                                            log_content = ''.join(error_lines)
                                            break
                                    except UnicodeDecodeError:
                                        continue
                                
                                if log_content:
                                    error_info += f'\n最后几行日志:\n{log_content}'
                                else:
                                    error_info += '\n日志文件: <无法解码>'
                            except Exception as e:
                                error_info += f'\n读取日志失败: {str(e)}'
                        
                        raise Exception(error_info)
                
                # 检查PDF是否生成成功
                pdf_file = f'{safe_name}.pdf'
                if not os.path.exists(pdf_file):
                    raise Exception('PDF文件未生成')
                
                # 清理辅助文件
                aux_extensions = ['.aux', '.log', '.out', '.toc', '.fls', '.fdb_latexmk']
                for ext in aux_extensions:
                    aux_file = f'{safe_name}{ext}'
                    if os.path.exists(aux_file):
                        try:
                            os.remove(aux_file)
                        except:
                            pass  # 清理失败不影响主要流程
                
                return 's'
                
            finally:
                os.chdir(original_cwd)
            
        except Exception as e:
            self.log_callback(f'PDF生成失败: {str(e)}')
            return 'err'


def create_cli():
    """Create CLI interface using the NovelDownloader class"""
    print('本程序完全免费(此版本为WEB版，目前处于测试阶段)\nGithub: https://github.com/ying-ck/fanqienovel-downloader\n作者：Yck & qxqycb & lingo34')
    print('优化增强版 - 支持YAML配置文件')

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='番茄小说下载器', add_help=False)
    parser.add_argument('--id', type=str, help='直接下载指定ID的小说')
    parser.add_argument('--config', type=str, default='config.yaml', help='配置文件路径')
    parser.add_argument('-h', '--help', action='store_true', help='显示帮助信息')
    parser.add_argument('config_file', nargs='?', help='配置文件路径（兼容旧格式）')
    
    args = parser.parse_args()
    
    if args.help:
        print('\n使用方法:')
        print('  python src/main.py                    # 使用默认配置文件并进入交互模式')
        print('  python src/main.py --config [配置文件] # 使用指定配置文件')
        print('  python src/main.py --id [小说ID]      # 直接下载指定ID的小说')
        print('  python src/main.py --help            # 显示此帮助信息')
        print('\n示例:')
        print('  python src/main.py --id 7520128677003136024')
        print('  python src/main.py --config my_config.yaml --id 7520128677003136024')
        print('\n配置文件示例请参考 config.yaml')
        return
    
    # 确定配置文件路径 (兼容旧格式)
    config_path = args.config
    if args.config_file:
        config_path = args.config_file
    
    # 加载配置
    if os.path.exists(config_path):
        print(f'📄 加载配置文件: {config_path}')
        config = Config.from_yaml(config_path)
    else:
        if config_path != 'config.yaml':
            print(f'⚠️ 配置文件不存在: {config_path}')
        print('📄 使用默认配置')
        config = Config()
    
    # 显示当前配置摘要
    print(f'\n📋 当前配置摘要:')
    print(f'  🗂️  输出格式: TXT({config.enable_txt}) JSON(必须) EPUB({config.enable_epub}) HTML({config.enable_html}) LaTeX({config.enable_latex}) PDF({config.enable_pdf})')
    print(f'  ⚡ 线程数: {config.thread_count}')
    print(f'  ⏱️  延时模式: {config.delay_mode} ({config.delay[0]}-{config.delay[1]}ms)')
    print(f'  📁 JSON目录: {config.bookstore_dir}')
    print(f'  📁 下载目录: {config.download_dir}')
    
    downloader = NovelDownloader(config)

    # Check for backup
    backup_folder_path = 'C:\\Users\\Administrator\\fanqie_down_backup'
    if os.path.exists(backup_folder_path):
        choice = input("检测到备份文件夹，否使用备份据？1.使用备份  2.跳过：")
        if choice == '1':
            if os.path.isdir(backup_folder_path):
                source_folder_path = os.path.dirname(os.path.abspath(__file__))
                for item in os.listdir(backup_folder_path):
                    source_item_path = os.path.join(backup_folder_path, item)
                    target_item_path = os.path.join(source_folder_path, item)
                    if os.path.isfile(source_item_path):
                        if os.path.exists(target_item_path):
                            os.remove(target_item_path)
                        shutil.copy2(source_item_path, target_item_path)
                    elif os.path.isdir(source_item_path):
                        if os.path.exists(target_item_path):
                            shutil.rmtree(target_item_path)
                        shutil.copytree(source_item_path, target_item_path)
            else:
                print("备份文件夹不存在，无法使用备份数据。")
        elif choice != '2':
            print("入无效，请重新运行程序并正确输入。")
    else:
        print("程序还未备份")
    
    # 如果提供了--id参数，直接下载并退出
    if args.id:
        print(f'\n🚀 开始直接下载小说ID: {args.id}')
        result = downloader.download_novel(args.id)
        if result:
            print('✅ 下载完成')
        else:
            print('❌ 下载失败，请检查小说ID是否正确')
        return

    while True:
        print('\n输入书的id直接下载\n输入下面的数字进入其他功能:')
        print('''
1. 更新小说
2. 搜索
3. 批量下载
4. 设置
5. 备份
6. 退出
        ''')

        inp = input()

        if inp == '1':
            downloader.update_all_novels()

        elif inp == '2':
            while True:
                key = input("请输入搜索关键词（直接Enter返回）：")
                if key == '':
                    break
                results = downloader.search_novel(key)
                if not results:
                    print("没有找到相关书籍。")
                    continue

                for i, book in enumerate(results):
                    print(f"{i + 1}. 名称：{book['book_data'][0]['book_name']} "
                          f"作者：{book['book_data'][0]['author']} "
                          f"ID：{book['book_data'][0]['book_id']} "
                          f"字数：{book['book_data'][0]['word_number']}")

                while True:
                    choice = input("请选择一个结果, 输入 r 以重新搜索：")
                    if choice == "r":
                        break
                    elif choice.isdigit() and 1 <= int(choice) <= len(results):
                        chosen_book = results[int(choice) - 1]
                        downloader.download_novel(chosen_book['book_data'][0]['book_id'])
                        break
                    else:
                        print("输入无效，请重新输入。")

        elif inp == '3':
            urls_path = 'urls.txt'
            if not os.path.exists(urls_path):
                print(f"未找到'{urls_path}'，将为您创建一个新的文件。")
                with open(urls_path, 'w', encoding='UTF-8') as file:
                    file.write("# 输入小说链接，一行一个\n")

            print(f"\n请在文本编辑器中打开并编辑 '{urls_path}'")
            print("在文件中输入小说链接，一行一个")

            if platform.system() == "Windows":
                os.system(f'notepad "{urls_path}"')
            elif platform.system() == "Darwin":
                os.system(f'open -e "{urls_path}"')
            else:
                if os.system('which nano > /dev/null') == 0:
                    os.system(f'nano "{urls_path}"')
                elif os.system('which vim > /dev/null') == 0:
                    os.system(f'vim "{urls_path}"')
                else:
                    print(f"请使用任意文本编辑器手动编辑 {urls_path} 文件")

            print("\n编辑完成后按Enter键继续...")
            input()

            with open(urls_path, 'r', encoding='UTF-8') as file:
                content = file.read()
                urls = content.replace(' ', '').split('\n')

            for url in urls:
                if url and url[0] != '#':
                    print(f'开始下载链接: {url}')
                    status = downloader.download_novel(url)
                    if not status:
                        print(f'链接: {url} 下载失败。')
                    else:
                        print(f'链接: {url} 下载完成。')

        elif inp == '4':
            print('请选择项目：1.正文段首占位符 2.章节下载间隔延迟 3.小说保存路径 4.小说保存方式 5.设置下载线程数')
            inp2 = input()
            if inp2 == '1':
                tmp = input('请输入正文段首占位符(当前为"%s")(直接Enter不更改)：' % config.kgf)
                if tmp != '':
                    config.kgf = tmp
                config.kg = int(input('请输入正文段首占位符数（当前为%d）：' % config.kg))
            elif inp2 == '2':
                print('由于迟过小造成的后果请自行负责。\n请输入下载间隔随机延迟')
                config.delay[0] = int(input('下限（当前为%d）毫秒）：' % config.delay[0]))
                config.delay[1] = int(input('上限（当前为%d）（毫秒）：' % config.delay[1]))
            elif inp2 == '3':
                print('tip:设置为当前目录点取消')
                time.sleep(1)
                path = input("\n请输入保存目录的完整路径:\n(直接按Enter用当前目录)\n").strip()
                if path == "":
                    config.save_path = os.getcwd()
                else:
                    if not os.path.exists(path):
                        try:
                            os.makedirs(path)
                            config.save_path = path
                        except:
                            print("无法创建目录，将使用当前目录")
                            config.save_path = os.getcwd()
                    else:
                        config.save_path = path
            elif inp2 == '4':
                print('请选择：1.保存为单个 txt 2.分章保存 3.保存为 epub 4.保存为 HTML 网页格式 5.保存为 LaTeX')
                inp3 = input()
                try:
                    config.save_mode = SaveMode(int(inp3))
                except ValueError:
                    print('请正确输入!')
                    continue
            elif inp2 == '5':
                config.xc = int(input('请输入下载线程数：'))
            else:
                print('请正确输入!')
                continue

            # Save config
            with open(downloader.config_path, 'w', encoding='UTF-8') as f:
                json.dump({
                    'kg': config.kg,
                    'kgf': config.kgf,
                    'delay': config.delay,
                    'save_path': config.save_path,
                    'save_mode': config.save_mode.value,
                    'space_mode': config.space_mode,
                    'xc': config.xc
                }, f)
            print('设置完成')

        elif inp == '5':
            downloader.backup_data('C:\\Users\\Administrator\\fanqie_down_backup')
            print('备份完成')

        elif inp == '6':
            break

        else:
            # Try to download novel directly
            if downloader.download_novel(inp):
                print('下载完成')
            else:
                print('请输入有效的选项或书籍ID。')


if __name__ == "__main__":
    create_cli()