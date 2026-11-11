from fastapi import FastAPI

from app.routers import chat_routes

app = FastAPI()

app.include_router(chat_routes.router)


@app.get("/")
async def sample_endpoint():
    return {"greeting":"Hello from FastAPI! This is the Document Digester Chatbot backend"}
