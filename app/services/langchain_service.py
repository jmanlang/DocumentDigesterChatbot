from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from app.docs_indexer.config import Config

config = Config.from_env()
if config.inference_backend == "ollama":
    gemma_chat_model = ChatOllama(
        model=config.inference_model,
        base_url=config.inference_base_url,
        temperature=config.inference_temperature,
    )
else:
    from langchain_openai import ChatOpenAI

    gemma_chat_model = ChatOpenAI(
        model=config.inference_model,
        base_url=config.inference_base_url,
        temperature=config.inference_temperature,
        use_responses_api=False,
    )

coder_assistant_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a chatbot that answers questions about "
               "Git, Docker, LangChain, and LangGraph. "
               "You give helpful, concise, accurate answers. "
               "If you don't know the answer, say you don't know. "
               "Politely refuse questions that are inappropriate or off-topic."),
    ("user", "{question}")
])

def build_chat_chain():
    return coder_assistant_prompt | gemma_chat_model
