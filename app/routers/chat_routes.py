import logging
import re

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from app.services.vectordb_service import embed_query, retrieve_context
from pydantic import BaseModel

from app.services.langchain_service import build_chat_chain, OFF_TOPIC_RESPONSE

logger = logging.getLogger(__name__)

chat_router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

class ChatRequest(BaseModel):
    question:str

chat_chain = build_chat_chain()


@chat_router.post("/")
async def ask_model(chat_request:ChatRequest):
    """Answer with retrieved documentation while keeping blocking work off the event loop."""
    try:
        # Run the embedding work in a separate thread
        logger.info("Creating embeddings for the user query...")
        query_embedding = await run_in_threadpool(embed_query, chat_request.question)

        # Get relevant embeddings based on user query
        logger.info("Retrieving relevant embeddings based on user query...")
        context, sources = await run_in_threadpool(retrieve_context, query_embedding)
        answer = await chat_chain.ainvoke({
            "question": chat_request.question, "context": context,
        })
        
        if str(answer.text).strip().casefold() == OFF_TOPIC_RESPONSE.casefold():
            answer.content = OFF_TOPIC_RESPONSE
            return answer
        
        # Drop invented citation numbers that don't exist
        valid_references = set(re.findall(r"^- \[(\d+)\]", sources, flags=re.MULTILINE))
        answer_text = re.sub(
            r"(```[\s\S]*?```|`[^`\n]*`)|\[(\d+)\]",
            lambda match: match.group(0)
            if match.group(1) or match.group(2) in valid_references else "",
            str(answer.text),
        )

        # Append references to regular answers
        logger.info("Appending references to LLM answers...")
        source_list = sources or "No document sources were retrieved."
        answer.content = f"{answer_text}\n\nRetrieved sources:\n\n{source_list}"
        return answer
    except Exception:
        logger.exception("Chat backend request failed")
        raise HTTPException(
            status_code=503,
            detail="The embedding, vector database, or inference service is unavailable.",
        )
