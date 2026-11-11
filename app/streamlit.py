import streamlit as st
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
    except (URLError, HTTPError) as error:
        return f"Could not reach the API: {error}"

    if isinstance(data, dict):
        return data.get("content") or data.get("answer")
    
    return str(data)

st.set_page_config(page_title="CoderGPT", page_icon="X")
st.header("Welcome to CoderGPT")

with st.sidebar:
    st.subheader("About CoderGPT")
    st.markdown(
        """
        CoderGPT is your friendly assistant for understanding key software technologies.
        It specializes in: Git, Docker, LangChain, and LangGraph.
        """
    )

    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


if prompt := st.chat_input("Ask me anything technical"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Thinking..."):
        answer = ask_backend(prompt)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.markdown(answer)
