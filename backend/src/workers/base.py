from abc import ABC,abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel

class WorkerResult(BaseModel):
    success: bool
    output: Optional[Any] = None
    error: Optional[Any] = None
    metadata: Dict[str,Any] = {}

class BaseWorker(ABC):
    
    def __init__(self,config: Dict[str,Any]):
        self.config = config

    @abstractmethod
    def process(self, input_data: Dict[str,Any]) -> WorkerResult:
        pass

    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        pass