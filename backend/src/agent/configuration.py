import os
from typing import Any, Optional
from pydantic import BaseModel, Field

from langchain_core.runnables import RunnableConfig

class Configuration(BaseModel):
    planning_model: str = Field(
        default="gemini-2.0-flash",
        description = "Decide how to accomplish the task (multi-step reasoning)"
    )

    perception_model: str = Field(
        default="gemini-2.0-flash",
        description="Understand what's happening on screen and what user wants"
    )

    web_model: str = Field(
        default="gemini-2.0-flash",
        description="Interact with web content"
    )

    content_model: str = Field(
        default="gemini-2.0-flash",
        description="Process and transform content"
    )

    max_retries: int = Field(
        default=3,
        description="Number retries per worker"
    )

    pdf_output_dir: str = Field(
        default="./outputs",
        description="Directory to save generated PDFs"
    )

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        
        configurable = (
            config['configurable'] if config and "configurable" in config else {}
        )

        raw_values: dict[str, Any] = {
            name: os.environ.get(name.upper() , configurable.get(name))
            for name in cls.model_fields.keys()
        }

        values = {k: v for k,v in raw_values.items() if v is not None}

        return cls(**values)