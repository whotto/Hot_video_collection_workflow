import os
import requests
from bs4 import BeautifulSoup
import time
import re
import json
import argparse
from urllib.parse import quote, urlencode
import random
import string
import logging
from datetime import datetime
import pickle
import hashlib
from fake_useragent import UserAgent
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import sys
from seleniumwire import webdriver
from playwright.sync_api import sync_playwright
import yt_dlp
from exa_py import Exa
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# 加载环境变量
load_dotenv()

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VideoExtractor:
    """视频数据提取器"""
    
    def __init__(self):
        """初始化"""
        # 加载环境变量
        load_dotenv()
        
        # API密钥
        self.exa_api_key = os.getenv('EXA_API_KEY')
        if not self.exa_api_key:
            logger.error("EXA_API_KEY environment variable is not set")
            raise ValueError("EXA_API_KEY is required")
        
        # Chrome路径
        self.chrome_binary_path = os.getenv('CHROME_BINARY_PATH')
        if not self.chrome_binary_path:
            logger.warning("CHROME_BINARY_PATH environment variable is not set")
        
        # 初始化Cookies存储
        self.cookies_dir = 'cookies'
        if not os.path.exists(self.cookies_dir):
            os.makedirs(self.cookies_dir)
        
        # 加载已保存的cookies
        self.load_cookies()
        
        # 设置User-Agent
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        
        self.setup_driver()
        
    def setup_driver(self):
        """配置浏览器驱动"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
    
    def load_cookies(self):
        """加载保存的cookies"""
        self.cookies = {}
        for platform in ['douyin', 'kuaishou', 'bilibili', 'youtube']:
            cookie_file = os.path.join(self.cookies_dir, f'{platform}_cookies.pkl')
            if os.path.exists(cookie_file):
                try:
                    with open(cookie_file, 'rb') as f:
                        self.cookies[platform] = pickle.load(f)
                except Exception as e:
                    logger.error(f"Error loading cookies for {platform}: {str(e)}")
    
    def save_cookies(self, platform, cookies):
        """保存cookies"""
        cookie_file = os.path.join(self.cookies_dir, f'{platform}_cookies.pkl')
        try:
            with open(cookie_file, 'wb') as f:
                pickle.dump(cookies, f)
        except Exception as e:
            logger.error(f"Error saving cookies for {platform}: {str(e)}")
    
    def get_headers(self, platform='default', with_cookie=True):
        """获取请求头"""
        headers = {
            'User-Agent': UserAgent().random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        if with_cookie and platform in self.cookies:
            headers['Cookie'] = self.cookies[platform]
            
        if platform == 'douyin':
            headers.update({
                'authority': 'www.douyin.com',
                'referer': 'https://www.douyin.com/',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1'
            })
        elif platform == 'kuaishou':
            headers.update({
                'authority': 'www.kuaishou.com',
                'origin': 'https://www.kuaishou.com',
                'content-type': 'application/json'
            })
            
        return headers
    
    def verify_video_url(self, url):
        """验证视频 URL 是否有效"""
        try:
            # 检查 URL 格式
            if not url:
                return False
                
            # 检查是否是小红书域名
            if 'xiaohongshu.com' in url or 'xhslink.com' in url:
                return True  # 小红书的链接我们直接返回 True，因为需要登录才能验证
                
            # 检查是否是抖音视频域名
            valid_domains = [
                'v3-web.douyinvod.com',
                'v9-web.douyinvod.com',
                'v26-web.douyinvod.com',
                'v3.douyinvod.com',
                'v9.douyinvod.com',
                'v26.douyinvod.com'
            ]
            
            # 构造请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/604.1',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Range': 'bytes=0-10',  # 只请求前10个字节来验证
                'Referer': 'https://www.douyin.com/',
                'Origin': 'https://www.douyin.com'
            }
            
            for domain in valid_domains:
                if domain in url:
                    # 发送 HEAD 请求验证视频
                    response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
                    
                    if response.status_code == 200 or response.status_code == 206:
                        content_type = response.headers.get('content-type', '')
                        if 'video' in content_type.lower() or 'application/octet-stream' in content_type.lower():
                            logger.info(f"Valid video URL: {url}")
                            return True
                    
                    logger.warning(f"URL returned status code: {response.status_code}")
                    return False
            
            logger.warning(f"Invalid video domain: {url}")
            return False
                
        except Exception as e:
            logger.error(f"Error verifying URL: {str(e)}")
            return False
    
    def _parse_count(self, count_str):
        """解析数量字符串，处理单位（万、w、k等）"""
        if count_str is None:
            return 0
            
        if isinstance(count_str, (int, float)):
            return int(count_str)
            
        try:
            # 转换为小写并移除空格和逗号
            count_str = str(count_str).lower().strip().replace(',', '')
            
            # 处理中文数字单位
            if '亿' in count_str:
                base = float(count_str.replace('亿', ''))
                return int(base * 100000000)
            elif '万' in count_str or 'w' in count_str:
                base = float(count_str.replace('万', '').replace('w', ''))
                return int(base * 10000)
            elif 'k' in count_str:
                base = float(count_str.replace('k', ''))
                return int(base * 1000)
            else:
                return int(float(count_str))
        except (ValueError, TypeError):
            return 0
    
    def format_results(self, results):
        """格式化搜索结果"""
        if not results:
            return "找到 0 个结果:\n"
        
        output = [f"找到 {len(results)} 个结果:\n"]
        
        for i, result in enumerate(results, 1):
            if not isinstance(result, dict):
                continue
                
            # 添加平台信息
            platform = result.get('platform', '未知')
            output.append(f"\n{i}. 平台: {platform}")
            
            # 添加标题（如果有）
            title = result.get('title', '').strip()
            if title and title != '未知':
                output.append(f"   标题: {title}")
                
            # 添加作者（如果有）
            author = result.get('author', '').strip()
            if author and author != '未知':
                output.append(f"   作者: {author}")
                
            # 添加URL（必需）
            url = result.get('url', '').strip()
            if url:
                output.append(f"   链接: {url}")
                
            # 添加描述（如果有）
            text = result.get('text', '').strip()
            if text and text != '未知' and len(text) > 0:
                # 限制描述长度
                if len(text) > 200:
                    text = text[:197] + '...'
                output.append(f"   描述: {text}")
                
            # 添加统计信息（如果有）
            views = result.get('views', 0)
            if views and isinstance(views, (int, float)) and views > 0:
                output.append(f"   播放量: {views:,}")
                
            likes = result.get('likes', 0)
            if likes and isinstance(likes, (int, float)) and likes > 0:
                output.append(f"   点赞数: {likes:,}")
                
            comments = result.get('comments', 0)
            if comments and isinstance(comments, (int, float)) and comments > 0:
                output.append(f"   评论数: {comments:,}")
                
            shares = result.get('shares', 0)
            if shares and isinstance(shares, (int, float)) and shares > 0:
                output.append(f"   分享数: {shares:,}")
                
            # 添加发布时间（如果有）
            publish_time = result.get('publish_time', '').strip()
            if publish_time and publish_time != '未知' and len(publish_time) > 0:
                output.append(f"   发布时间: {publish_time}")
                
            # 添加标签（如果有）
            tags = result.get('tags', [])
            if tags:
                output.append(f"   标签: {', '.join(tags)}")
                
        return "\n".join(output)
        
    def clean_title(self, title: str) -> str:
        """清理标题，移除URL和多余字符"""
        # 移除URL
        title = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', title)
        # 移除HTML标签
        title = re.sub(r'<[^>]+>', '', title)
        # 处理HTML实体
        title = title.replace('&quot;', '"').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        # 移除多余空白字符
        title = ' '.join(title.split())
        # 移除开头的特殊字符
        title = re.sub(r'^[【\[\(].*?[\]\)】]', '', title).strip()
        return title.strip()

    def extract_tags(self, text):
        """从文本中提取标签
        Args:
            text: 标题或描述文本
        Returns:
            list: 标签列表
        """
        tags = []
        
        # 提取#标签（包括中英文）
        hashtags = re.findall(r'#([^#\s]+?)(?=\s|$|#)', text)
        for tag in hashtags:
            # 移除标签中的URL
            tag = re.sub(r'http[s]?://\S+', '', tag)
            if tag and not re.match(r'^[\W_]+$', tag):  # 确保标签不是只有特殊字符
                tags.append(tag)
        
        # 提取【】中的关键词
        brackets = re.findall(r'【([^】]+)】', text)
        tags.extend([b.strip() for b in brackets if b.strip()])
        
        # 提取[]中的关键词
        square_brackets = re.findall(r'\[([^\]]+)\]', text)
        tags.extend([b.strip() for b in square_brackets if b.strip()])
        
        # 去重并清理
        cleaned_tags = []
        for tag in tags:
            # 移除标签中的特殊字符
            cleaned_tag = re.sub(r'[^\w\s\u4e00-\u9fff]+', '', tag)
            cleaned_tag = cleaned_tag.strip()
            if cleaned_tag and len(cleaned_tag) > 1:  # 确保标签长度大于1
                cleaned_tags.append(cleaned_tag)
        
        return list(dict.fromkeys(cleaned_tags))  # 去重

    def search_kuaishou(self, keyword):
        """使用 Exa.ai 搜索快手视频"""
        video_data = []
        max_results = 10  # 增加到10个视频
        
        try:
            from exa_py import Exa
            import re
            
            exa = Exa(api_key=self.exa_api_key)
            
            logger.info(f"搜索快手，关键词：{keyword}")
            
            # 使用更精确的搜索关键词组合
            search_queries = [
                f"{keyword} site:kuaishou.com/short-video",
                f"{keyword} site:www.kuaishou.com/video",
                f"{keyword} site:v.kuaishou.com",
                f"快手 {keyword} 视频",
                f"{keyword} 快手 作品"
            ]
            
            # 有效的快手视频URL模式
            valid_url_patterns = [
                'kuaishou.com/short-video',
                'v.kuaishou.com'
            ]
            
            # 无效的URL模式
            invalid_url_patterns = [
                'kuaishou.com/about',
                'kuaishou.com/contact',
                'kuaishou.com/privacy',
                'kuaishou.com/terms',
                'ir.kuaishou.com',
                'activity.kuaishou.com',
                'ai.kuaishou.com',
                'kling.kuaishou.com',
                'www.kuaishou.com/search',
                'www.kuaishou.com/profile'
            ]
            
            seen_urls = set()  # 用于去重
            
            for query in search_queries:
                if len(video_data) >= max_results:
                    break
                
                logger.info(f"尝试搜索: {query}")
                
                try:
                    # 使用基本搜索方法
                    results = exa.search(
                        query,
                        num_results=20,  # 增加搜索结果数量以提高找到有效视频的概率
                        include_domains=["kuaishou.com"]
                    )
                    
                    if not results or not hasattr(results, 'results'):
                        continue
                    
                    for result in results.results:
                        if len(video_data) >= max_results:
                            break
                        
                        url = result.url if hasattr(result, 'url') else None
                        if not url:
                            continue
                            
                        # 移除URL参数
                        clean_url = url.split('?')[0]
                        
                        # 检查是否已经处理过这个URL
                        if clean_url in seen_urls:
                            continue
                        seen_urls.add(clean_url)
                        
                        # 检查是否是无效的URL
                        if any(pattern in clean_url for pattern in invalid_url_patterns):
                            continue
                            
                        # 检查是否是有效的视频URL
                        if not any(pattern in clean_url for pattern in valid_url_patterns):
                            continue
                            
                        # 获取标题和描述
                        title = result.title if hasattr(result, 'title') else None
                        text = result.text if hasattr(result, 'text') else None
                        author = result.author if hasattr(result, 'author') else None
                        views = result.views if hasattr(result, 'views') else 0
                        likes = result.likes if hasattr(result, 'likes') else 0
                        comments = result.comments if hasattr(result, 'comments') else 0
                        shares = result.shares if hasattr(result, 'shares') else 0
                        publish_time = result.published if hasattr(result, 'published') else None
                        
                        # 确保所有字段都是字符串或数字
                        title = str(title).strip() if title is not None else '未知'
                        text = str(text).strip() if text is not None else ''
                        author = str(author).strip() if author is not None else '未知'
                        
                        # 处理数字字段
                        try:
                            views = str(views).replace('万', '0000').replace('w', '0000').replace('k', '000').replace(',', '')
                            views = int(float(views)) if views else 0
                        except (ValueError, TypeError):
                            views = 0
                        
                        try:
                            likes = str(likes).replace('万', '0000').replace('w', '0000').replace('k', '000').replace(',', '')
                            likes = int(float(likes)) if likes else 0
                        except (ValueError, TypeError):
                            likes = 0
                        
                        try:
                            comments = str(comments).replace('万', '0000').replace('w', '0000').replace('k', '000').replace(',', '')
                            comments = int(float(comments)) if comments else 0
                        except (ValueError, TypeError):
                            comments = 0
                        
                        try:
                            shares = str(shares).replace('万', '0000').replace('w', '0000').replace('k', '000').replace(',', '')
                            shares = int(float(shares)) if shares else 0
                        except (ValueError, TypeError):
                            shares = 0
                        
                        publish_time = str(publish_time).strip() if publish_time is not None else ''
                        
                        # 清理HTML实体和多余空白
                        title = title.replace('&amp;', '&').strip()
                        text = text.replace('&amp;', '&').strip()
                        author = author.replace('&amp;', '&').strip()
                        
                        # 如果标题为空或未知，尝试从文本中提取
                        if not title or title == '未知':
                            # 从文本中提取可能的标题
                            if text:
                                # 取第一行或前100个字符作为标题
                                potential_title = text.split('\n')[0][:100]
                                if potential_title:
                                    title = potential_title
                        
                        # 如果作者为空或未知，尝试从标题或文本中提取
                        if not author or author == '未知':
                            # 尝试从标题中提取作者名
                            author_patterns = [
                                r'@(\w+)',  # @用户名
                                r'【(.+?)】',  # 【作者名】
                                r'「(.+?)」',  # 「作者名」
                                r'作者[：:]\s*(.+?)\s',  # 作者：xxx
                                r'by\s+(.+?)\s',  # by xxx
                            ]
                            for pattern in author_patterns:
                                match = re.search(pattern, title + ' ' + text)
                                if match:
                                    potential_author = match.group(1).strip()
                                    if potential_author:
                                        author = potential_author
                                        break
                        
                        # 提取标签
                        tags = self.extract_tags(title + ' ' + text)
                        
                        video = {
                            'platform': 'kuaishou',
                            'title': self.clean_title(title),
                            'url': clean_url,
                            'text': text,
                            'author': author,
                            'play_count': views,
                            'like_count': likes,
                            'comment_count': comments,
                            'share_count': shares,
                            'publish_time': publish_time,
                            'tags': tags
                        }
                        
                        video_data.append(video)
                        logger.info(f"找到快手视频：{video['title']} ({video['url']})")
                    
                except Exception as e:
                    logger.error(f"搜索快手视频时出错: {str(e)}")
                    continue
                
        except Exception as e:
            logger.error(f"搜索快手出错: {str(e)}")
        
        if video_data:
            logger.info(f"找到 {len(video_data)} 个快手视频")
            return video_data
            
        logger.warning("未找到快手视频")
        return []
    
    def search(self, platform, keyword):
        """在指定平台搜索视频"""
        if hasattr(self, f'search_{platform}'):
            return getattr(self, f'search_{platform}')(keyword)
        else:
            raise ValueError(f'不支持的平台: {platform}')
    
    def search_bilibili(self, keyword):
        """B站搜索实现"""
        results = []
        # 实现B站搜索逻辑
        return results
    
    def search_douyin(self, keyword):
        """抖音搜索实现"""
        results = []
        # 实现抖音搜索逻辑
        return results
    
    def search_kuaishou(self, keyword):
        """快手搜索实现"""
        results = []
        # 实现快手搜索逻辑
        return results
    
    def extract_video_info(self, url):
        """提取视频信息"""
        info = {
            'title': '',
            'author': '',
            'play_count': 0,
            'like_count': 0,
            'comment_count': 0,
            'share_count': 0,
            'publish_time': '',
            'description': ''
        }
        # 实现视频信息提取逻辑
        return info
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'driver'):
            self.driver.quit()

def main():
    """主程序"""
    import argparse
    import json
    from dotenv import load_dotenv
    
    try:
        # 加载环境变量
        load_dotenv()
        
        # 初始化提取器
        extractor = VideoExtractor()
        
        # 创建命令行参数解析器
        parser = argparse.ArgumentParser(description='视频搜索工具')
        parser.add_argument('keyword', help='搜索关键词')
        parser.add_argument('--platform', help='搜索平台 (youtube/kuaishou/xiaohongshu/weixin_video/all)', default='all')
        parser.add_argument('--json', action='store_true', help='以JSON格式输出结果')
        args = parser.parse_args()
        
        print(f"\n搜索关键词: {args.keyword}")
        print(f"搜索平台: {args.platform}")
        
        extractor = VideoExtractor()
        
        if args.platform == 'all':
            results = extractor.search_all_platforms(args.keyword)
            for platform, platform_results in results.items():
                if platform_results:
                    print(f"\n{platform} 平台搜索结果:")
                    print(extractor.format_results(platform_results))
        else:
            search_method = getattr(extractor, f'search_{args.platform}', None)
            if search_method:
                results = search_method(args.keyword)
                print(extractor.format_results(results))
            else:
                print(f"不支持的平台: {args.platform}")
    
    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
