from fastapi import APIRouter
from pydantic import BaseModel

from app.services.langchain_service import build_chat_chain

chat_router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

class ChatRequest(BaseModel):
    question:str

chat_chain = build_chat_chain()


@chat_router.post("/")
async def ask_model(chat_request:ChatRequest):
    return await chat_chain.ainvoke({"question":chat_request.question})
