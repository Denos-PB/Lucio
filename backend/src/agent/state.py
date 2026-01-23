from __future__ import annotations

from email import message
from typing import Optional, Literal, TypedDict
from typing_extensions import Annotated
import operator

from langgraph.graph import add_messages

class OverallState(TypedDict, total=False):
    request_id: str
    input_prompt: str
    execute_plan: str
    messages: Annotated[list, add_messages]
    status: Literal["pending", "running", "partial", "completed", "failed"]
    errors: Annotated[list[str], operator.add]

class PerceptionState(TypedDict, total=False):
    screen_image: Optional[str]
    prompt: Optional[str]
    screen_analysis: Optional[str]
    keyword: Optional[str]
    detected_url: Optional[str]

class WebState(TypedDict, total=False):
    url: Optional[str]
    prompt: Optional[str]
    keyword: Optional[str]
    summary: Optional[str]
    output_text: Optional[str]

class ContentState(TypedDict, total=False):
    prompt: Optional[str]
    output_text_from_url: Optional[str]
    pdf_file_path: Optional[str]
    pdf_generated: bool