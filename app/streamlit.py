import streamlit as st
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import uuid

API_URL = "http://127.0.0.1:8000/chat/"

def ask_backend(question: str) -> str:
    payload = json.dumps({"question": question}).encode()
    request = Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode())
    except OSError as error:
        return f"Could not get an answer from the API: {error}"

    if isinstance(data, dict):
        return data.get("content") or data.get("answer")
    
    return str(data)



st.set_page_config(page_title="CoderGPT", page_icon=":material/chat:")

def new_chat():
    chat_id = str(uuid.uuid4())
    st.session_state.chats[chat_id] = {"title": "New chat", "messages": []}
    st.session_state.current_chat_id = chat_id

if "chats" not in st.session_state:
    st.session_state.chats = {}
    new_chat()

current_chat = st.session_state.chats[st.session_state.current_chat_id]

with st.sidebar:
    st.title("CoderGPT")
    st.caption("Documentation assistant for Git, Docker, LangChain, and LangGraph")

    if st.button("New chat", icon=":material/add:", width="stretch"):
        new_chat()
        st.rerun()

    st.subheader("Chats")
    for chat_id, chat in reversed(st.session_state.chats.items()):
        is_current = chat_id == st.session_state.current_chat_id

        if st.button(
            chat["title"],
            key=chat_id,
            icon=":material/chat_bubble:",
            type="primary" if is_current else "tertiary",
            width="stretch",
        ):
            st.session_state.current_chat_id = chat_id
            st.rerun()

    st.divider()

    if st.button("Delete this chat", icon=":material/delete:", width="stretch"):
        del st.session_state.chats[st.session_state.current_chat_id]

        if st.session_state.chats:
            st.session_state.current_chat_id = next(reversed(st.session_state.chats))
        else:
            new_chat()
        st.rerun()
    
    with st.expander("About CoderGPT"):
        st.markdown(
            """
            CoderGPT is your friendly assistant for understanding key software technologies.
            It specializes in: Git, Docker, LangChain, and LangGraph.
            """
        )

st.header("Welcome to CoderGPT")

for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


if prompt := st.chat_input("Ask me anything technical"):

    if not current_chat["messages"]:
        current_chat["title"] = prompt[:40]
    
    current_chat["messages"].append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Thinking..."):
        answer = ask_backend(prompt)

    current_chat["messages"].append({"role": "assistant", "content": answer})
    st.rerun()
