from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="gemma4:e2b",
    base_url="http://localhost:11434",
    temperature=.2
)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are CoderGPT, a chatbot that answers questions about "
               "Git, Docker, LangChain, and LangGraph. "
               "You give helpful, concise, accurate answers. "
               "If you don't know the answer, say you don't know. "
               "Politely refuse questions that are inappropriate or off-topic."),
    ("user", "{input}")
])

def get_general_chain():
    return prompt | llm
