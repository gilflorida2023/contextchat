import streamlit as st
import ollama
from time import sleep

def initialize_session():
    """Initializes session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "file_content" not in st.session_state:
        st.session_state.file_content = ""
    if "uploaded_file_obj" not in st.session_state:
        st.session_state.uploaded_file_obj = None

# --- Initialization ---
initialize_session()
st.title("DeepSeek Chat with File Context")

# --- File Uploader ---
with st.sidebar:
    st.header("File Upload")
    uploaded_file = st.file_uploader(
        "Upload a text file for context",
        type=None,
        key="file_uploader_widget"
    )
    # Process file only if it's a new upload
    if uploaded_file is not None and uploaded_file != st.session_state.uploaded_file_obj:
        st.session_state.uploaded_file_obj = uploaded_file
        try:
            file_bytes = uploaded_file.read()
            try:
                st.session_state.file_content = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    st.session_state.file_content = file_bytes.decode("latin-1")
                except UnicodeDecodeError:
                    st.error("Failed to decode file. Please upload a plain text file (UTF-8 or Latin-1).")
                    st.session_state.file_content = ""
                    st.session_state.messages = []
                    st.session_state.uploaded_file_obj = None

            if st.session_state.file_content:
                st.session_state.messages = [] # Clear history on new file
                st.success("File context loaded! Chat history cleared.")

        except Exception as e:
            st.error(f"Error processing file: {e}")
            st.session_state.file_content = ""
            st.session_state.messages = []
            st.session_state.uploaded_file_obj = None

    elif uploaded_file is None and st.session_state.uploaded_file_obj is not None:
         st.session_state.uploaded_file_obj = None
         st.session_state.file_content = ""
         st.session_state.messages = []
         st.info("File removed. Context and chat history cleared.")

    if st.session_state.file_content:
        st.sidebar.success("Context file is active.")
    else:
        st.sidebar.warning("Upload a text file to provide context.")


# --- Chat History Display ---
# Display messages from session state *before* handling new input
st.header("Chat History")
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Chat Input and Processing ---
prompt = st.chat_input("Ask your question...")

if prompt:
    # Check if file content is loaded
    if not st.session_state.file_content:
        st.error("Please upload a valid text file first using the sidebar!")
        st.stop()

    # 1. Display the user's new message *immediately*
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Add user message to session state
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 3. Prepare context for the model (using updated state)
    full_context = [
        {"role": "system", "content": f"Use the following text as context:\n\n{st.session_state.file_content}\n\nAnswer the user's questions based on this context."}
    ]
    # Add message history
    full_context.extend(st.session_state.messages)


    # 4. Get and display assistant response (with streaming)
    try:
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            stream = ollama.chat(
                model="deepseek-r1:1.5b", # Or your preferred model
                messages=full_context,
                stream=True,
            )
            for chunk in stream:
                chunk_content = chunk.get('message', {}).get('content', '')
                if chunk_content:
                    full_response += chunk_content
                    response_placeholder.markdown(full_response + "▌")

            response_placeholder.markdown(full_response) # Display final response

        # 5. Add assistant response to session state *after* it's fully generated and displayed
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response
        })

    except Exception as e:
        st.error(f"Error communicating with Ollama: {str(e)}")
        # If an error occurs, remove the user message we optimistically added,
        # otherwise it will look like the user asked a question that got no answer.
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
             st.session_state.messages.pop()


# No st.rerun() needed here, Streamlit handles the loop
