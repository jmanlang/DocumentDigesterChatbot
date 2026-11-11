from fastapi import FastAPI

from app.routers import chat_routes

app = FastAPI()

app.include_router(chat_routes.chat_router)


@app.get("/")
async def get_welcome_message():
    return {"greeting":"Hello from FastAPI! This is the Document Digester Chatbot backend"}
