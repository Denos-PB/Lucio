from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel

from .tool.screen_streamer import start_screen_stream
from .agent.graph import build_graph
from .agent.state import OverallState
from dotenv import load_dotenv

load_dotenv()

start_screen_stream(interval=1.0)

workflow = build_graph().compile()

app = FastAPI(title="Lucio Agent API")

class RunRequest(BaseModel):
    prompt: str
    url: str | None = None  # Optional: user can provide URL directly as fallback

class RunResponse(BaseModel):
    request_id: str
    status: str
    pdf_file_path: str | None = None
    pdf_generated: bool = False
    errors: list[str] = []

@app.post("/run",  response_model=RunResponse)
def run_agent(req: RunRequest) -> RunResponse:
    request_id = str(uuid4())
    initial_state: OverallState = {
        "request_id": request_id,
        "input_prompt": req.prompt,
        "detected_url": req.url,  # Use provided URL if available (fallback)
        "status": "pending",
        "messages": [],
        "errors": [],
    }

    final_state = workflow.invoke(initial_state)

    return RunResponse(
        request_id=request_id,
        status=final_state.get("status", "unknown"),
        pdf_file_path=final_state.get("pdf_file_path"),
        pdf_generated=bool(final_state.get("pdf_generated", False)),
        errors=final_state.get("errors", []),
    )