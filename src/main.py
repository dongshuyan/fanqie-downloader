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
        # For CLI: Use tqdm directly
        if not hasattr(self, '_pbar'):
            self._pbar = tqdm(total=total, desc=desc)
        self._pbar.update(1)  # Update by 1 instead of setting n directly

        # For web: Return progress info as dict
        return {
            'current': current,
            'total': total,
            'percentage': (current / total * 100) if total > 0 else 0,
            'description': desc,
            'chapter_title': chapter_title
        }

    def download_novel(self, novel_id: int) -> str:
        """Download a novel"""
        try:
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
                        title, _ = future_to_chapter[future]
                        try:
                            content = future.result()
                            if content:
                                clean_title = title.strip()
                                novel_content[clean_title] = content  # 保存时去除标题的空白字符
                                
                                # 额外保存单独的章节TXT文件到Chapters文件夹
                                chapter_filename = f"{self._sanitize_filename(clean_title)}.txt"
                                chapter_path = os.path.join(chapters_dir, chapter_filename)
                                
                                with open(chapter_path, 'w', encoding='UTF-8') as f:
                                    f.write(f"{clean_title}\n\n{content}")
                                    
                        except Exception as e:
                            self.log_callback(f'下载章节失败 {title}: {str(e)}')

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
            
            # 返回结果
            if results:
                self.log_callback(f'🎉 下载完成！已保存格式: {", ".join(results)}')
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
        """Download a single chapter with retries"""
        if title in existing_content:
            self.zj[title] = existing_content[title]  # Add this
            return existing_content[title]

        self.log_callback(f'下载章节: {title}')
        retries = 3
        last_error = None

        while retries > 0:
            try:
                content = self._download_chapter_content(chapter_id)
                if content == 'err':  # Add this check
                    raise Exception('Download failed')

                time.sleep(random.randint(
                    self.config.delay[0],
                    self.config.delay[1]
                ) / 1000)

                # Handle cookie refresh
                if content == 'err':
                    self.tcs += 1
                    if self.tcs > 7:
                        self.tcs = 0
                        self._get_new_cookie(self.tzj)
                    continue  # Try again with new cookie

                # Save progress periodically
                self.cs += 1
                if self.cs >= 5:
                    self.cs = 0
                    self._save_progress(title, content)

                self.zj[title] = content  # Add this
                return content

            except Exception as e:
                last_error = e
                retries -= 1
                if retries == 0:
                    self.log_callback(f'下载失败 {title}: {str(e)}')
                    break
                time.sleep(1)

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
        """Get novel info and chapter list"""
        url = f'https://fanqienovel.com/page/{novel_id}'
        response = req.get(url, headers=self.headers)
        ele = etree.HTML(response.text)

        chapters = {}
        a_elements = ele.xpath('//div[@class="chapter"]/div/a')
        if not a_elements:  # Add this check
            return 'err', {}, []

        for a in a_elements:
            href = a.xpath('@href')
            if not href:  # Add this check
                continue
            chapters[a.text] = href[0].split('/')[-1]

        title = ele.xpath('//h1/text()')
        status = ele.xpath('//span[@class="info-label-yellow"]/text()')

        if not title or not status:  # Check both title and status
            return 'err', {}, []

        return title[0], chapters, status

    def _download_chapter_content(self, chapter_id: int, test_mode: bool = False) -> str:
        """Download content with fallback and better error handling"""
        headers = self.headers.copy()
        headers['cookie'] = self.cookie

        for attempt in range(3):
            try:
                # Try primary method
                response = req.get(
                    f'https://fanqienovel.com/reader/{chapter_id}',
                    headers=headers,
                    timeout=10
                )
                response.raise_for_status()

                content = '\n'.join(
                    etree.HTML(response.text).xpath(
                        '//div[@class="muye-reader-content noselect"]//p/text()'
                    )
                )

                if test_mode:
                    return content

                try:
                    return self._decode_content(content)
                except:
                    # Try alternative decoding mode
                    try:
                        return self._decode_content(content, mode=1)
                    except:
                        # Fallback HTML processing
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
                        return result

            except Exception as e:
                # Try alternative API endpoint
                try:
                    response = req.get(
                        f'https://fanqienovel.com/api/reader/full?itemId={chapter_id}',
                        headers=headers
                    )
                    content = json.loads(response.text)['data']['chapterData']['content']

                    if test_mode:
                        return content

                    return self._decode_content(content)
                except:
                    if attempt == 2:  # Last attempt
                        if test_mode:
                            return 'err'
                        raise Exception(f"Download failed after 3 attempts: {str(e)}")
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

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for different platforms"""
        illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        illegal_chars_rep = ['＜', '＞', '：', '＂', '／', '＼', '｜', '？', '＊']
        for old, new in zip(illegal_chars, illegal_chars_rep):
            filename = filename.replace(old, new)
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
        """使用pdflatex将LaTeX文件编译为PDF"""
        try:
            import subprocess
            
            latex_file = f'{safe_name}.tex'
            latex_path = os.path.join(output_dir, latex_file)
            
            # 检查LaTeX文件是否存在
            if not os.path.exists(latex_path):
                raise Exception(f'LaTeX文件不存在: {latex_path}')
            
            # 检查pdflatex是否可用
            try:
                subprocess.run(['pdflatex', '--version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                raise Exception('pdflatex未安装或不在PATH中。请安装LaTeX发行版（如TeX Live或MiKTeX）')
            
            # 编译LaTeX为PDF
            self.log_callback('正在使用pdflatex编译PDF...')
            
            # 切换到输出目录执行pdflatex
            original_cwd = os.getcwd()
            try:
                os.chdir(output_dir)
                
                # 运行pdflatex，通常需要运行两次以正确生成目录和引用
                for i in range(2):
                    result = subprocess.run(
                        ['pdflatex', '-interaction=nonstopmode', latex_file],
                        capture_output=True,
                        text=True,
                        timeout=300  # 5分钟超时
                    )
                    
                    if result.returncode != 0:
                        # 如果失败，尝试查看日志
                        log_file = f'{safe_name}.log'
                        error_info = f'pdflatex编译失败 (返回码: {result.returncode})'
                        if os.path.exists(log_file):
                            # 读取最后几行日志
                            try:
                                with open(log_file, 'r', encoding='utf-8', errors='ignore') as log_f:
                                    lines = log_f.readlines()
                                    # 取最后20行
                                    error_lines = lines[-20:] if len(lines) > 20 else lines
                                    error_info += '\n最后几行日志:\n' + ''.join(error_lines)
                            except:
                                pass
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

    # 检查命令行参数
    import sys
    config_path = 'config.yaml'
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print('\n使用方法:')
            print('  python src/main.py                    # 使用默认配置文件 config.yaml')
            print('  python src/main.py [配置文件路径]      # 使用指定配置文件')
            print('  python src/main.py --help            # 显示此帮助信息')
            print('\n配置文件示例请参考 config.yaml')
            return
        else:
            config_path = sys.argv[1]
    
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