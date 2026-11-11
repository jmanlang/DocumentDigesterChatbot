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


# import streamlit as st

# # Now actual UI stuff----------------

# # NOTE: "with" is the mechanism in streamlit that renders stuff on the page

# # Basic Header
# st.header("Welcome to CoderGPT")

# # Store the previous chats (streamlit handles internal state for you! nice)
# if "messages" not in st.session_state:
#     st.session_state.messages = [] # Start empty... of course

# # Here's the component that displays whatever messages are saved in state
# for message in st.session_state.messages:
#     with st.chat_message(message["role"]):
#         st.markdown(message["content"])

# # Sidebar
# with st.sidebar:

#     # Button that switches to our st_file_input.py
#     # NOTE: any non-main file needs to be in a folder called "pages"
#     if st.button("Switch to File Input"):
#         st.switch_page("pages/st_file_input.py")

#     st.subheader("About CoderGPT")
#     st.markdown(
#         """
#         CoderGPT is your friendly assistant for understanding key software technologies.
#         It specifically specializes in: Git, Docker, LangChain, and LangGraph

#         Its knowledge base is always expanding.
#         """
#     )

#     # Button that wipes the chat transcript
#     if st.button("Clear Chat"): # IF this gets clicked, clear the chat
#         st.session_state.messages = []
#         st.rerun() # Auto-refresh so we see the clear chat



# # User input box (btw "prompt" is a built-in streamlit variable)
# if prompt := st.chat_input("Ask me anything technical"):

#     # Save and display user messages
#     st.session_state.messages.append({"role": "user", "content": prompt})
#     with st.chat_message("user"):
#         st.markdown(prompt)

#     # # Get the LLM's response and attach a spinner while it thinks
#     # with st.spinner("Pondering..."):
#     #     response = chain.invoke({"input":prompt})

#     # # Display the LLM reponse once it's done thinking
#     # st.session_state.messages.append({"role": "assistant", "content": response.content})
#     # with st.chat_message("assistant"):
#     #      st.markdown(response.content)