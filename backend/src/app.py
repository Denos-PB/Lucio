from uuid import uuid4
import json

from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .tool.screen_streamer import start_screen_stream
from .agent.graph import build_graph
from .agent.state import OverallState
from .db import init_db, SessionLocal, Conversation


load_dotenv()
init_db()

start_screen_stream(interval=1.0)

workflow = build_graph().compile()

app = FastAPI(title="Lucio Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    prompt: str
    url: str | None = None


class RunResponse(BaseModel):
    request_id: str
    status: str
    pdf_file_path: str | None = None
    pdf_generated: bool = False
    errors: list[str] = []


@app.post("/run", response_model=RunResponse)
def run_agent(req: RunRequest) -> RunResponse:
    request_id = str(uuid4())
    initial_state: OverallState = {
        "request_id": request_id,
        "input_prompt": req.prompt,
        "detected_url": req.url,
        "status": "pending",
        "messages": [],
        "errors": [],
    }

    final_state = workflow.invoke(initial_state)

    db: Session = SessionLocal()
    try:
        conv = Conversation(
            request_id=request_id,
            prompt=req.prompt,
            url=final_state.get("url"),
            status=final_state.get("status", "unknown"),
            pdf_file_path=final_state.get("pdf_file_path"),
            pdf_generated=bool(final_state.get("pdf_generated", False)),
            errors=json.dumps(final_state.get("errors", []), ensure_ascii=False),
        )
        db.add(conv)
        db.commit()
    finally:
        db.close()

    return RunResponse(
        request_id=request_id,
        status=final_state.get("status", "unknown"),
        pdf_file_path=final_state.get("pdf_file_path"),
        pdf_generated=bool(final_state.get("pdf_generated", False)),
        errors=final_state.get("errors", []),
    )