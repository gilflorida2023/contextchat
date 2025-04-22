import streamlit as st
import ollama
from time import sleep

def initialize_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "file_content" not in st.session_state:
        st.session_state.file_content = ""

initialize_session()

st.title("DeepSeek Chat with File Context")

uploaded_file = st.file_uploader("Upload any text file for context", type=None)
if uploaded_file:
    try:
        st.session_state.file_content = uploaded_file.read().decode("utf-8")
        st.session_state.messages = []
        st.success("File content loaded successfully!")
    except UnicodeDecodeError:
        st.error("Failed to decode file as text. Please upload a text-based file.")
        st.session_state.file_content = ""

# Display existing messages first
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Ask your question...")
if prompt:
    if not st.session_state.file_content:
        st.warning("Please upload a valid text file first!")
        st.stop()

    # Add user question to session and display immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare context with system message
    full_context = [
        {"role": "system", "content": st.session_state.file_content}
    ] + st.session_state.messages

    try:
        # Generate and display assistant response
        with st.chat_message("assistant"):
            response_container = st.empty()
            full_response = ""
            
            for chunk in ollama.chat(
                model="deepseek-r1:32b",
                #model="deepseek-r1:1.5b",
                messages=full_context,
                stream=True,
            ):
                full_response += chunk["message"]["content"]
                response_container.markdown(full_response + "▌")
            
            response_container.markdown(full_response)
        
        # Add final response to session
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response
        })
    
    except Exception as e:
        st.error(f"Error communicating with Ollama: {str(e)}")
