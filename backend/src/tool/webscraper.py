import requests
from bs4 import BeautifulSoup
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse

class WebScraper:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def extract_content(self,url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            for script in soup(["script","style",]):
                script.decompose()

            title = soup.title.string if soup.title else "No title"

            main_content = soup.find(['article', 'main', 'div', 'section'])
            full_text = main_content.get_text(separator=' ', strip=True) if main_content else soup.get_text(separator=' ', strip=True)

            main_content_text = main_content.get_text(separator=' ', strip=True) if main_content else None
            
            return title, main_content_text, full_text
        
        except Exception as e:
            print(f"Error extracting content from {url}: {e}")
            return None, None, None
        
    def search_keyword_in_content(self,content: str, keyword: str) -> str:

        if not content or not keyword:
            return ""
        
        sentences = content.split('.')
        relevant_sentences = [
            s.strip() for s in sentences 
            if keyword.lower() in s.lower()
        ]

        return ". ".join(relevant_sentences[:5]) + "."
    
    def get_quick_summary(self,content: str, keyword: Optional[str] = None) -> str:
        
        if not content:
            return ""
        
        preview = content[:500].split('.')[:2]
        summary = ". ".join(preview) + "."

        if keyword:
            keyword_context = self.search_keyword_in_content(content, keyword)
            if keyword_context:
                summary = f"Found '{keyword}': {keyword_context[:200]}..."

        return summary
    
    def get_extended_summary(self, content: str) -> str:
        if not content:
            return ""
        
        extended = content[:2000]

        if len(content) > 2000:
            extended += "...[content truncated for PDF]"

        return extended


web_scraper = WebScraper()

def scrape_and_summarize(url:str, keyword: Optional[str] = None) -> dict:

    title, _, full_content = web_scraper.extract_content(url)

    if not full_content:
        return {
            'title': 'Error',
            'url': url,
            'quick_summary': 'Could not access webpage',
            'extended_text': 'Failed to scrape content',
            'full_content': '',
            'keyword_found': False
        }
    
    quick_summary = web_scraper.get_quick_summary(full_content, keyword)
    extended_text = web_scraper.get_extended_summary(full_content)
    keyword_found = keyword.lower() in full_content.lower() if keyword else False

    return {
        'title': title or 'Untitled',
        'url': url,
        'quick_summary': quick_summary,
        'extended_text': extended_text,
        'full_content': full_content,
        'keyword_found': keyword_found
    }