from __future__ import annotations

from email import message
from typing import Optional, Literal, TypedDict
from typing_extensions import Annotated
import operator

from langgraph.graph import add_messages

class OverallState(TypedDict, total=False):
    request_if: str
    user_prompt: str
    enhanced_prompt: Optional[str]
    messages: Annotated[list, add_messages]
    status: Literal["pending", "running", "partial", "completed", "failed"]
    errors: Annotated[list[str], operator.add]

class PromptEnhancerState(TypedDict, total=False):
    input_prompt: str
    enhanced_prompt: Optional[str]
    main_statement: Optional[str]
    keywords: Optional[str]
    summary: Optional[str]
    status: Literal["pending", "running", "completed", "failed"]
    errors: Annotated[list[str],operator.add]
