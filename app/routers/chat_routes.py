from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from app.services.vectordb_service import embed_query
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
    embedding = await run_in_threadpool(embed_query, chat_request.question)
    #return {"embedding": embedding.tolist()}
    return await chat_chain.ainvoke({"question":chat_request.question})
