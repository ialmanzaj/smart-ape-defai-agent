from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import logging
from typing import Optional

from agent.initialize_agent import initialize_agent
from agent.run_agent import run_agent
from db.setup import setup

load_dotenv()

app = FastAPI(title="Smart Ape - AI-Powered DeFi Wealth Manager")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup SQLite tables
setup()

# Initialize the agent
agent_executor = initialize_agent()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatInput(BaseModel):
    input: str
    conversation_id: int


@app.post("/api/chat")
async def chat(chat_input: ChatInput):
    try:
        config = {"configurable": {"thread_id": chat_input.conversation_id}}

        # Create an async generator for the streaming response
        async def generate_response():
            async for chunk in run_agent(chat_input.input, agent_executor, config):
                yield chunk

        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Content-Type": "text/event-stream",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        return JSONResponse(
            status_code=500, content={"error": "An unexpected error occurred"}
        )


@app.get("/")
async def root():
    return {"message": "Smart Ape API is running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
