import re
from typing import Optional
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from configuration import Configuration
from state import OverallState, PerceptionState, WebState, ContentState
from prompt import (
    PLANNING_MODEL_PROMPT,
    PERCEPTION_MODEL_PROMPT,
    WEB_MODEL_PROMPT,
    CONTENT_MODEL_PROMPT
)
from tool.screen_streamer import get_current_screen
from tool.webscraper import scrape_and_summarize
from tool.pdf_generator import save_to_pdf


class AgentNodes:
    def __init__(self, config: Configuration):
        self.config = config
        self.planning_model = ChatGoogleGenerativeAI(model=config.planning_model)
        self.perception_model = ChatGoogleGenerativeAI(model=config.perception_model)
        self.web_model = ChatGoogleGenerativeAI(model=config.web_model)
        self.content_model = ChatGoogleGenerativeAI(model=config.content_model)


    def _extract_url(self,text: str) -> Optional[str]:
        if not text:
            return None
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        matches = re.findall(url_pattern, text)
        return matches[0] if matches else None

    def _extract_keywords(self, text: str, user_query: str) -> Optional[str]:
        if user_query:
            common_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'}
            words = user_query.lower().split()
            keywords =[w for w in words if len(w) >= 3 and w not in common_words]
            return ', '.join(keywords[:5]) if keywords else None
        return None


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
2. Detected URL(s) if any
3. Keywords relevant to the task
4. Inferred user intent"""
            
            message = HumanMessage(
                content=[
                    {"type" : "text", "text" : perception_prompt},
                    {"type":"image_url", "image_url" : {"url" : f"data:image/png;base64,{screen_image}"}}
                ]
            )

            response = self.perception_model.invoke([message])
            response_text = response.content

            detected_url = self._extract_url(str(response_text))

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

            content_prompt = f"""{CONTENT_MODEL_PROMPT}

USER REQUEST: {content_state['prompt']}
ORIGINAL CONTENT: {content[:2000]}

Format and finalize this content for PDF generation.
Ensure it's well-structured, readable, and meets the user's requirements."""
            
            response = self.content_model.invoke([HumanMessage(content=content_prompt)])
            final_content = response.content

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