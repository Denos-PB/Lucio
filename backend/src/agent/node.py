import re
import httpx
from typing import Optional
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

from .configuration import Configuration
from .state import OverallState, PerceptionState, WebState, ContentState
from .prompt import (
    PLANNING_MODEL_PROMPT,
    PERCEPTION_MODEL_PROMPT,
    WEB_MODEL_PROMPT,
    CONTENT_MODEL_PROMPT,
)

from ..tool.screen_streamer import get_current_screen
from ..tool.webscraper import scrape_and_summarize
from ..tool.pdf_generator import save_to_pdf


class AgentNodes:
    def __init__(self, config: Configuration):
        self.config = config
        self.planning_model = ChatOllama(model=config.planning_model)
        self.perception_model = ChatOllama(model=config.perception_model)
        self.web_model = ChatOllama(model=config.web_model)
        self.content_model = ChatOllama(model=config.content_model)


    def _extract_url(self, text: str) -> Optional[str]:
        """Extract URL from text - handles multiple formats and patterns."""
        if not text:
            return None
        
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+[a-zA-Z0-9]'
        matches = re.findall(url_pattern, text)
        if matches:
            url = matches[0].rstrip('.,;:!?)')
            return url
        
        url_label_patterns = [
            r'URL:\s*(https?://[^\s<>"{}|\\^`\[\]]+[a-zA-Z0-9])',
            r'URL:\s*([a-zA-Z0-9][a-zA-Z0-9\-\.]*[a-zA-Z0-9]+\.[a-zA-Z]{2,})',
            r'Detected URL\(s\):\s*(https?://[^\s<>"{}|\\^`\[\]]+[a-zA-Z0-9])',
            r'Detected URL\(s\):\s*URL:\s*([a-zA-Z0-9][a-zA-Z0-9\-\.]*[a-zA-Z0-9]+\.[a-zA-Z]{2,})',
        ]
        
        for pattern in url_label_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                domain = matches[0].strip().rstrip('.,;:!?)')
                if not domain.startswith(('http://', 'https://')):
                    return f"https://{domain}"
                return domain
        
        context_patterns = [
            r'(?:address bar|URL|website|domain|link)[:\s]+([a-zA-Z0-9][a-zA-Z0-9\-\.]*[a-zA-Z0-9]+\.[a-zA-Z]{2,})',
            r'([a-zA-Z0-9][a-zA-Z0-9\-\.]*[a-zA-Z0-9]+\.[a-zA-Z]{2,})(?:\s+in\s+the\s+address\s+bar|\s+is\s+the\s+URL)',
        ]
        
        for pattern in context_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                domain = matches[0].strip().rstrip('.,;:!?)')
                if not domain.startswith(('http://', 'https://')):
                    return f"https://{domain}"
                return domain
        
        standalone_domain_pattern = r'\b([a-zA-Z0-9][a-zA-Z0-9\-]*\.)+[a-zA-Z]{2,}\b'
        matches = re.findall(standalone_domain_pattern, text, re.IGNORECASE)
        if matches:
            common_domains = ['example.com', 'localhost', '127.0.0.1']
            for match in matches:
                if match.lower() not in common_domains and len(match) > 5:
                    domain = match.strip().rstrip('.,;:!?)')
                    if not domain.startswith(('http://', 'https://')):
                        return f"https://{domain}"
                    return domain
        
        return None

    def _extract_keywords(self, text: str, user_query: str) -> Optional[str]:
        if user_query:
            common_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'}
            words = user_query.lower().split()
            keywords =[w for w in words if len(w) >= 3 and w not in common_words]
            return ', '.join(keywords[:5]) if keywords else None
        return None

    def _call_llava_with_image(self, prompt: str, image_b64: str) -> str:
        if image_b64.startswith("data:image"):
            image_b64 = image_b64.split(",")[1]
        
        payload = {
            "model": self.config.perception_model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
        }
        
        resp = httpx.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=400,
        )
        resp.raise_for_status()
        data = resp.json()

        return data.get("response", "")


    def planning_node(self, state: OverallState) -> OverallState:
        try:
            user_request = state.get('input_prompt', '')

            planning_prompt = f"""{PLANNING_MODEL_PROMPT}

USER REQUEST: {user_request}

Create a step-by-step plan to accomplish this task:
1. Analyze current screen
2. Extract relevant information
3. Summarize content
4. Generate PDF

Provide a brief execution plan."""
            
            response=self.planning_model.invoke([HumanMessage(content=planning_prompt)])
            plan = response.content
            
            state['execute_plan'] = str(plan)
            state.setdefault('messages', []).append(
                HumanMessage(content=f"[Planning] {plan}")
            )
            state['status'] = 'running'

            return state
        
        except Exception as e:
            state['status'] = 'failed'
            state.setdefault('errors', []).append(f"Planning node error: {str(e)}")

            return state

    def perception_node(self, state: OverallState) -> OverallState:
        try:
            existing_url = state.get('detected_url')
            if existing_url:
                state['detected_url'] = existing_url
                state['status'] = 'running'
                return state

            perception_state: PerceptionState = {
                'prompt': state.get('input_prompt', ''),
                'screen_image' : None,
                'screen_analysis': None,
                'keyword': None,
                'detected_url': None
            }

            screen_image = get_current_screen()
            if not screen_image:
                state['status'] = 'failed'
                state.setdefault('errors',[]).append("Failed to capture screen")
                return state

            perception_state['screen_image'] = screen_image
            
            perception_prompt = f"""{PERCEPTION_MODEL_PROMPT}

USER QUERY: {perception_state['prompt']}

Analyze the screenshot provided and the user query.

Provide:
1. Description of what's visible on screen
2. URL: [the URL from the address bar or visible on screen - write it exactly as you see it]
3. Keywords: [relevant keywords]
4. Intent: [what the user wants to do]"""
            
            response_text = self._call_llava_with_image(perception_prompt, screen_image)

            print(f"[DEBUG] LLaVA response: {response_text[:500]}")

            detected_url = self._extract_url(str(response_text))

            print(f"[DEBUG] Extracted URL: {detected_url}")
            
            if not detected_url:
                direct_prompt = """Look at this screenshot. What URL is displayed in the browser's address bar at the top? Write ONLY the URL, nothing else. If you see 'example.com', write 'example.com'. If you see 'https://example.com', write 'https://example.com'."""
                direct_response = self._call_llava_with_image(direct_prompt, screen_image)
                detected_url = self._extract_url(direct_response)
                print(f"[DEBUG] Direct prompt extracted URL: {detected_url}")

            perception_state['screen_analysis'] = str(response_text)
            perception_state['detected_url'] = detected_url
            perception_state['keyword'] = self._extract_keywords(
                str(response_text),
                perception_state['prompt'] or ''
            )

            state['screen_image'] = perception_state['screen_image']
            state['screen_analysis'] = perception_state['screen_analysis']
            state['detected_url'] = perception_state['detected_url']
            state['keyword'] = perception_state['keyword']

            state.setdefault('messages', []).append(
                HumanMessage(content=f"[Perception] {response_text[:200]}...")
            )
            state['status'] = 'running'

            return state
        
        except Exception as e:
            state['status'] = 'failed'
            state.setdefault('errors', []).append(f"Perception node error: {str(e)}")

            return state

    def web_node(self, state: OverallState) -> OverallState:
        try:
            web_state: WebState = {
                'url': state.get('detected_url'),
                'prompt' : state.get('input_prompt', ''),
                'keyword': state.get('keyword'),
                'title' : None,
                'summary' : None,
                'output_text' : None
            }

            if not web_state['url']:
                state['status'] = 'failed'
                state.setdefault('errors', []).append("No URL detected for web scraping")
                return state

            scraped_data = scrape_and_summarize(
                web_state['url'],
                keyword=web_state['keyword']
            )

            if not scraped_data.get('full_content'):
                state['status'] = 'failed'
                state.setdefault('errors', []).append(
                    f"Failed to scrape content from {web_state['url']}"
                )
                return state

            web_prompt = f"""{WEB_MODEL_PROMPT}

USER REQUEST: {web_state['prompt']}
SCRAPED TITLE: {scraped_data.get('title', 'Untitled')}
SCRAPED CONTENT: {scraped_data.get('extended_text', '')[:3000]}

Process this web content according to the user's request.
Extract and format the most relevant information."""

            response = self.web_model.invoke([HumanMessage(content=web_prompt)])
            processed_content = response.content

            web_state['title'] = scraped_data.get('title', 'Untitled')
            web_state['summary'] = scraped_data.get('quick_summary', '')
            web_state['output_text'] = str(processed_content)

            state['url'] = web_state['url']
            state['title'] = web_state['title']
            state['summary'] = web_state['summary']
            state['output_text'] = web_state['output_text']
            state['output_text_from_url'] = scraped_data.get('full_content', '')

            state.setdefault('messages', []).append(
                HumanMessage(content=f"[Web] Scraped and processed: {web_state['url']}")
            )
            state['status'] = 'running'

            return state

        except Exception as e:
            state['status'] = 'failed'
            state.setdefault('errors', []).append(f"Web node error: {str(e)}")
            return state

    def content_node(self, state:OverallState) -> OverallState:
        try:
            content_state: ContentState = {
                'prompt': state.get('input_prompt', ''),
                'title': state.get('title', 'Untitled Document'),
                'url': state.get('url'),
                'keyword': state.get('keyword'),
                'output_text_from_url': state.get('output_text_from_url', ''),
                'pdf_filename': None,
                'pdf_file_path': None,
                'pdf_generated': False
            }

            content = state.get('output_text', '')
            if not content:
                state['status'] = 'failed'
                state.setdefault('errors', []).append("No content available for PDF generation")
                return state

            content_to_process = content[:4000] if len(content) > 4000 else content
            
            content_prompt = f"""{CONTENT_MODEL_PROMPT}

USER REQUEST: {content_state['prompt']}

ORIGINAL CONTENT TO FORMAT:
{content_to_process}

TASK:
Transform the above content into a well-structured, readable document.
- Add clear headings to organize the content
- Format paragraphs properly
- Ensure the text flows naturally
- Make it professional and easy to read
- Preserve all important information

OUTPUT THE FORMATTED CONTENT NOW (no explanations, just the formatted content):"""
            
            response = self.content_model.invoke([HumanMessage(content=content_prompt)])
            raw_content = response.content

            if isinstance(raw_content, list):
                parts = []
                for part in raw_content:
                    if isinstance(part, str):
                        parts.append(part)
                    elif isinstance(part, dict) and "text" in part:
                        parts.append(str(part["text"]))
                final_content = " ".join(parts).strip()
            else:
                final_content = str(raw_content).strip()

            if final_content.startswith("Here is") or final_content.startswith("Here's"):
                lines = final_content.split('\n')
                final_content = '\n'.join(lines[1:]) if len(lines) > 1 else final_content

            pdf_result = save_to_pdf(
                title = str(content_state['title']),
                content=str(final_content),
                url=content_state['url'],
                keyword=content_state['keyword'],
                output_dir = self.config.pdf_output_dir
            )

            if not pdf_result.get('success'):
                state['status'] = 'failed'
                state.setdefault('errors', []).append(
                    f"PDF generation failed: {pdf_result.get('error', 'Unknown error')}"
                )
                return state

            content_state['pdf_filename'] = pdf_result.get('filename')
            content_state['pdf_file_path'] = pdf_result.get('file_path')
            content_state['pdf_generated'] = True

            state['pdf_filename'] = content_state['pdf_filename']
            state['pdf_file_path'] = content_state['pdf_file_path']
            state['pdf_generated'] = content_state['pdf_generated']

            state.setdefault('messages', []).append(
                HumanMessage(content=f"[Content] PDF generated: {content_state['pdf_filename']}")
            )
            state['status'] = 'completed'

            return state

        except Exception as e:
            state['status'] = 'failed'
            state.setdefault('errors', []).append(f"Content node error: {str(e)}")
            return state