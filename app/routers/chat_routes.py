from fastapi import APIRouter
from pydantic import BaseModel

from app.services.langchain_service import get_general_chain

router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

class ChatInputModel(BaseModel):
    input:str

chain = get_general_chain()


@router.post("/")
async def general_chat(chat:ChatInputModel):
    return await chain.ainvoke({"input":chat.input})
