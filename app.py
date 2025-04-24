import streamlit as st
import ollama
import json
import os
import hashlib
from time import sleep
import datetime

# --- Session State Initialization ---
def initialize_session():
    """Initializes session state variables if they don't exist."""
    defaults = {
        "messages": [],
        "file_content": "",
        "uploaded_file_obj": None,
        "available_models": [],
        "selected_model": None,
        "models_loaded": False,
        "ollama_error": None,
        "document_cache": {},  # {file_hash: {"content": str, "summary": str, "timestamp": str, "filename": str}}
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- Ollama Interaction ---
def get_ollama_models():
    """Fetches the list of models from Ollama, logs raw output, and updates session state."""
    st.session_state.ollama_error = None
    print("--- Attempting to fetch Ollama models... ---")
    try:
        models_data = ollama.list()
        print("--- ollama.list() raw response START ---")
        print(repr(models_data))
        print("--- ollama.list() raw response END ---")

        if hasattr(models_data, 'models') and isinstance(models_data.models, list):
            model_list = models_data.models
            valid_model_names = sorted([
                item.model for item in model_list
                if hasattr(item, 'model') and isinstance(getattr(item, 'model', None), str)
            ])
            st.session_state.available_models = valid_model_names
            print(f"--- Extracted model names: {valid_model_names} ---")
        else:
            print(f"--- ERROR: Expected response object with a 'models' attribute containing a list. Received type: {type(models_data)} ---")
            st.session_state.available_models = []

        st.session_state.models_loaded = True

        if not st.session_state.available_models:
            error_msg = "Ollama is running, but no valid models were extracted. Check terminal logs."
            print(f"--- Parsing completed, but resulted in empty model list. Raw models: {getattr(models_data, 'models', 'Attribute not found')} ---")
            st.session_state.ollama_error = error_msg
            return False
        else:
            st.session_state.ollama_error = None
            print("--- Models successfully loaded into session state. ---")
            return True

    except Exception as e:
        error_msg = f"Could not connect to Ollama or list models: {e}. Ensure Ollama is running."
        st.error(error_msg)
        print(f"--- Exception during ollama.list(): {type(e).__name__} - {e} ---")
        st.session_state.available_models = []
        st.session_state.selected_model = None
        st.session_state.models_loaded = True
        st.session_state.ollama_error = f"Connection/List Error: {e}"
        return False

# --- Helper Function: Generate File Hash ---
def get_file_hash(file_bytes):
    """Generates a SHA-256 hash of the file content for cache key."""
    return hashlib.sha256(file_bytes).hexdigest()

# --- Helper Function: Summarize Document ---
def summarize_document(content, model):
    """Uses the selected model to generate a summary of the document."""
    if not model:
        print("--- No model selected for summarization ---")
        return "Summary pending: Select a model to generate."
    try:
        prompt = (
            "Summarize the following document in 2-3 sentences, capturing the main points:\n\n"
            f"{content[:2000]}"  # Limit input to avoid token limits
        )
        print(f"--- Summarizing document with model {model} (first 100 chars): {content[:100]}... ---")
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )
        summary = response.get("message", {}).get("content", "")
        if not summary:
            print("--- Summary empty or not found in response ---")
            return "Summary could not be generated: Empty response."
        print(f"--- Generated summary: {summary[:100]}... ---")
        return summary.strip()
    except Exception as e:
        print(f"--- Error summarizing document: {type(e).__name__} - {e} ---")
        return f"Summary could not be generated: {str(e)}"

# --- Helper Function: Load/Save Cache to Disk ---
def save_cache_to_disk():
    """Saves the document cache to a JSON file."""
    try:
        print(f"--- Saving cache to document_cache.json: {len(st.session_state.document_cache)} entries ---")
        for file_hash, data in st.session_state.document_cache.items():
            print(f"--- Cache entry {file_hash}: filename={data['filename']}, content_len={len(data['content'])}, summary_len={len(data['summary'])} ---")
        with open("document_cache.json", "w") as f:
            json.dump(st.session_state.document_cache, f, indent=2)
    except Exception as e:
        print(f"--- Error saving cache to disk: {type(e).__name__} - {e} ---")

def load_cache_from_disk():
    """Loads the document cache from a JSON file if it exists."""
    try:
        if os.path.exists("document_cache.json"):
            with open("document_cache.json", "r") as f:
                st.session_state.document_cache = json.load(f)
            print(f"--- Loaded cache from document_cache.json: {len(st.session_state.document_cache)} entries ---")
        else:
            print("--- No document_cache.json found ---")
    except Exception as e:
        print(f"--- Error loading cache from disk: {type(e).__name__} - {e} ---")

# --- Application Start ---
initialize_session()
st.title("Ollama Chat")

# Load cache from disk at startup
load_cache_from_disk()

# --- Sidebar: Configuration ---
with st.sidebar:
    st.header("Configuration")

    if not st.session_state.models_loaded:
        with st.spinner("Connecting to Ollama and fetching models..."):
            get_ollama_models()

    if st.session_state.ollama_error:
        st.warning(st.session_state.ollama_error)
    elif st.session_state.models_loaded and not st.session_state.available_models:
        st.warning("Ollama connected, but no models found/extracted.")
    elif st.session_state.models_loaded:
        st.success(f"Ollama connected. {len(st.session_state.available_models)} models available.")

    if st.session_state.available_models:
        options = ["--- Select a Model ---"] + st.session_state.available_models
        current_selection = st.session_state.selected_model
        try:
            index = options.index(current_selection) if current_selection else 0
        except ValueError:
            index = 0
        selected = st.selectbox(
            "Select LLM Model:",
            options=options,
            key="selected_model_widget",
            index=index
        )
        widget_value = st.session_state.selected_model_widget
        if widget_value == "--- Select a Model ---":
            if st.session_state.selected_model is not None:
                st.session_state.selected_model = None
        elif widget_value != st.session_state.selected_model:
            st.session_state.selected_model = widget_value
            # Check if a summary is pending for the current file
            if st.session_state.file_content and st.session_state.uploaded_file_obj:
                file_hash = get_file_hash(st.session_state.uploaded_file_obj.read())
                if file_hash in st.session_state.document_cache:
                    if st.session_state.document_cache[file_hash]["summary"].startswith("Summary pending"):
                        with st.spinner("Generating document summary..."):
                            summary = summarize_document(
                                st.session_state.file_content, st.session_state.selected_model
                            )
                            st.session_state.document_cache[file_hash]["summary"] = summary
                            save_cache_to_disk()
                            st.success("Summary generated for cached document!")
    else:
        st.selectbox("Select LLM Model:", options=["--- Models Loading/Unavailable ---"], disabled=True)

    # --- File Uploader (Optional Context) ---
    st.header("Optional Context File")
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
            file_hash = get_file_hash(file_bytes)
            print(f"--- Processing uploaded file: {uploaded_file.name}, hash: {file_hash} ---")

            # Check if file is already in cache
            if file_hash in st.session_state.document_cache:
                st.session_state.file_content = st.session_state.document_cache[file_hash]["content"]
                print(f"--- Loaded cached content (len: {len(st.session_state.file_content)}) for {uploaded_file.name} ---")
                st.success("Loaded cached document content and summary!")
            else:
                # Decode file
                try:
                    st.session_state.file_content = file_bytes.decode("utf-8")
                    encoding = "UTF-8"
                except UnicodeDecodeError:
                    try:
                        st.session_state.file_content = file_bytes.decode("latin-1")
                        encoding = "Latin-1"
                    except UnicodeDecodeError:
                        st.error("Failed to decode file. Use plain text (UTF-8 or Latin-1).")
                        st.session_state.file_content = ""
                        st.session_state.uploaded_file_obj = None
                        print("--- File decode failed ---")
                        st.stop()

                print(f"--- Decoded file content (len: {len(st.session_state.file_content)}): {st.session_state.file_content[:100]}... ---")

                # Generate summary if model is selected
                summary = ""
                if st.session_state.selected_model:
                    with st.spinner("Generating document summary..."):
                        summary = summarize_document(st.session_state.file_content, st.session_state.selected_model)
                else:
                    summary = "Summary pending: Select a model to generate."

                # Store in cache
                st.session_state.document_cache[file_hash] = {
                    "content": st.session_state.file_content,
                    "summary": summary,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "filename": uploaded_file.name,
                }
                print(f"--- Stored in cache: filename={uploaded_file.name}, content_len={len(st.session_state.file_content)}, summary_len={len(summary)} ---")
                save_cache_to_disk()
                st.success(f"{encoding} file context loaded! Summary {'generated' if st.session_state.selected_model else 'pending'}.")

        except Exception as e:
            st.error(f"Error processing file: {e}")
            st.session_state.file_content = ""
            st.session_state.uploaded_file_obj = None
            print(f"--- File processing error: {type(e).__name__} - {e} ---")

    elif uploaded_file is None and st.session_state.uploaded_file_obj is not None:
        st.session_state.uploaded_file_obj = None
        st.session_state.file_content = ""
        st.info("File context removed.")
        print("--- File context removed ---")

    # Display context status
    if st.session_state.file_content:
        st.sidebar.success("Context file is active.")
        # Display content length and summary
        content_len = len(st.session_state.file_content)
        st.sidebar.markdown(f"**Content Length**: {content_len} characters")
        for file_hash, data in st.session_state.document_cache.items():
            if data["content"] == st.session_state.file_content:
                st.sidebar.markdown(f"**Document Summary**: {data['summary']}")
                st.sidebar.markdown(f"**Filename**: {data['filename']}")
                st.sidebar.markdown(f"**Cached**: {data['timestamp']}")
                break
    else:
        st.sidebar.info("No context file loaded.")

    # Debug: Show cache contents
    if st.session_state.document_cache:
        with st.expander("Debug: View Cache Contents"):
            st.json(st.session_state.document_cache)

# --- Chat History Display ---
st.header("Chat History")
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# --- Chat Input and Processing ---
prompt = st.chat_input("Select a model, then ask a question...")
if prompt:
    if not st.session_state.selected_model:
        st.error("⚠️ Please select a model from the sidebar first!")
        st.stop()

    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Prepare context for the model
    full_context = st.session_state.messages[:]
    system_prompt_content = "You are a helpful AI assistant."
    if st.session_state.file_content:
        for file_hash, data in st.session_state.document_cache.items():
            if data["content"] == st.session_state.file_content:
                system_prompt_content += (
                    f"\n\nUse the following document summary and context if relevant:\n"
                    f"**Summary**: {data['summary']}\n"
                    f"**Full Context**:\n---CONTEXT START---\n{st.session_state.file_content}\n---CONTEXT END---"
                )
                break
        else:
            system_prompt_content += (
                f"\n\nUse the following text as context if relevant:\n"
                f"---CONTEXT START---\n{st.session_state.file_content}\n---CONTEXT END---"
            )

    full_context.insert(0, {"role": "system", "content": system_prompt_content})

    try:
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            stream = ollama.chat(
                model=st.session_state.selected_model,
                messages=full_context,
                stream=True,
            )
            for chunk in stream:
                chunk_content = chunk.get('message', {}).get('content', '')
                if chunk_content:
                    full_response += chunk_content
                    response_placeholder.markdown(full_response + "▌")
            response_placeholder.markdown(full_response)

        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response
        })

    except Exception as e:
        st.error(f"Error during chat with Ollama (Model: {st.session_state.selected_model}): {str(e)}")
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
            st.session_state.messages.pop()
        print(f"--- Ollama Chat Exception: {type(e).__name__} - {e} ---")
