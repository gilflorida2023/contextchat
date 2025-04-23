import streamlit as st
import ollama
from time import sleep
import datetime # Needed for Model object types potentially

# --- Session State Initialization ---
def initialize_session():
    """Initializes session state variables if they don't exist."""
    defaults = {
        "messages": [],
        "file_content": "",
        "uploaded_file_obj": None,
        "available_models": [],
        "selected_model": None, # Start with no model selected
        "models_loaded": False, # Flag to track if model fetch attempt was made
        "ollama_error": None # Store potential connection error message
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- Ollama Interaction ---
def get_ollama_models():
    """Fetches the list of models from Ollama, logs raw output, and updates session state.
       Handles the ListResponse object directly."""
    st.session_state.ollama_error = None
    print("--- Attempting to fetch Ollama models... ---")
    try:
        # This returns an ollama._types.ListResponse object based on user debug output
        models_data = ollama.list()

        print("--- ollama.list() raw response START ---")
        # Use repr() for potentially more detailed object info in logs
        print(repr(models_data))
        print("--- ollama.list() raw response END ---")

        # Check if the response object has the 'models' attribute and it's a list
        if hasattr(models_data, 'models') and isinstance(models_data.models, list):
            model_list = models_data.models
            # Extract the 'model' attribute (which holds the name string) from each Model object
            valid_model_names = sorted([
                # Access the 'model' attribute of the Model object item
                item.model for item in model_list
                # Add checks to ensure item is an object with 'model' attribute
                if hasattr(item, 'model') and isinstance(getattr(item, 'model', None), str)
            ])
            st.session_state.available_models = valid_model_names
            print(f"--- Extracted model names (from attributes): {valid_model_names} ---")
        else:
             # Log if the structure is not as expected (e.g., no 'models' attribute)
             print(f"--- ERROR: Expected response object with a 'models' attribute containing a list. Received type: {type(models_data)} ---")
             st.session_state.available_models = []

        st.session_state.models_loaded = True

        # Check if any valid models were actually found after parsing
        if not st.session_state.available_models:
            error_msg = "Ollama is running, but no valid models were extracted from the response. Check terminal logs."
            # Add more detail to log if possible
            print(f"--- Parsing completed, but resulted in an empty list of model names. Raw models list from response: {getattr(models_data, 'models', 'Attribute not found')} ---")
            st.session_state.ollama_error = error_msg
            return False
        else:
            st.session_state.ollama_error = None # Clear error if models found
            print("--- Models successfully loaded into session state. ---")
            return True # Success

    except Exception as e:
        error_msg = f"Could not connect to Ollama or list models: {e}. Ensure Ollama is running."
        st.error(error_msg) # Show error in Streamlit UI
        print(f"--- Exception during ollama.list(): {type(e).__name__} - {e} ---") # Detailed print in terminal
        st.session_state.available_models = []
        st.session_state.selected_model = None
        st.session_state.models_loaded = True # Mark as attempted even on failure
        st.session_state.ollama_error = f"Connection/List Error: {e}" # Store specific error
        return False # Failure


# --- Application Start ---
initialize_session()
st.title("Ollama Chat")

# --- Sidebar: Configuration ---
with st.sidebar:
    st.header("Configuration")

    # Attempt to load models if not already attempted in this session
    if not st.session_state.models_loaded:
        with st.spinner("Connecting to Ollama and fetching models..."):
            get_ollama_models()

    # Display Ollama Status/Error
    if st.session_state.ollama_error:
        st.warning(st.session_state.ollama_error)
    # Check specifically if loaded and empty list vs not loaded at all
    elif st.session_state.models_loaded and not st.session_state.available_models:
         st.warning("Ollama connected, but no models found/extracted.")
    elif st.session_state.models_loaded:
        st.success(f"Ollama connected. {len(st.session_state.available_models)} models available.")

    # --- Model Selection Dropdown ---
    if st.session_state.available_models:
        # Prepare options, adding a placeholder if no model is selected yet
        options = ["--- Select a Model ---"] + st.session_state.available_models
        current_selection = st.session_state.selected_model
        try:
            # If a model is selected, its name is the value. Otherwise, the placeholder is shown (index 0).
            index = options.index(current_selection) if current_selection else 0
        except ValueError:
            index = 0 # Default to placeholder if selected model somehow invalid (e.g. uninstalled)

        selected = st.selectbox(
            "Select LLM Model:",
            options=options,
            key="selected_model_widget", # Use a distinct key for the widget
            index=index
        )

        # Update the actual selected model state based on widget's value
        widget_value = st.session_state.selected_model_widget
        if widget_value == "--- Select a Model ---":
            # Only update if it's actually changing to None
            if st.session_state.selected_model is not None:
                st.session_state.selected_model = None
                # Optional: Clear chat history when model selection is cleared
                # st.session_state.messages = []
                # st.rerun()
        elif widget_value != st.session_state.selected_model:
             st.session_state.selected_model = widget_value
             # Optional: Clear chat history when model changes? You might want this.
             # st.session_state.messages = []
             # st.rerun() # Rerun immediately to reflect change and potentially clear history visible
    else:
        # Show disabled box if no models loaded/found
        st.selectbox("Select LLM Model:", options=["--- Models Loading/Unavailable ---"], disabled=True)


    # --- File Uploader (Optional Context) ---
    st.header("Optional Context File")
    uploaded_file = st.file_uploader(
        "Upload a text file for context",
        type=None, # Allow any type, handle errors later
        key="file_uploader_widget"
    )

    # Process file only if it's a new upload
    if uploaded_file is not None and uploaded_file != st.session_state.uploaded_file_obj:
        st.session_state.uploaded_file_obj = uploaded_file
        try:
            file_bytes = uploaded_file.read()
            # Attempt decoding
            try:
                st.session_state.file_content = file_bytes.decode("utf-8")
                st.success("UTF-8 file context loaded!")
            except UnicodeDecodeError:
                 try:
                     st.session_state.file_content = file_bytes.decode("latin-1")
                     st.success("Latin-1 file context loaded!")
                 except UnicodeDecodeError:
                     st.error("Failed to decode file. Use plain text (UTF-8 or Latin-1).")
                     st.session_state.file_content = ""
                     st.session_state.uploaded_file_obj = None # Reset file obj

            # Optional: Clear chat history when a new context file is loaded
            # if st.session_state.file_content:
            #      st.session_state.messages = []

        except Exception as e:
            st.error(f"Error processing file: {e}")
            st.session_state.file_content = ""
            st.session_state.uploaded_file_obj = None

    # Handle file removal by user clicking 'x'
    elif uploaded_file is None and st.session_state.uploaded_file_obj is not None:
         st.session_state.uploaded_file_obj = None
         st.session_state.file_content = ""
         # Optional: Clear messages when file is removed
         # st.session_state.messages = []
         st.info("File context removed.")

    # Display context status
    if st.session_state.file_content:
        st.sidebar.success("Context file is active.")
    else:
        st.sidebar.info("No context file loaded.")


# --- Chat History Display ---
st.header("Chat History")
# Create a container for the chat history
chat_container = st.container()
with chat_container:
    # Display messages from session state
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# --- Chat Input and Processing ---
prompt = st.chat_input("Select a model, then ask a question...")

if prompt:
    # **** Check if a model is selected ****
    if not st.session_state.selected_model:
        st.error("⚠️ Please select a model from the sidebar first!")
        st.stop() # Stop processing if no model is chosen

    # 1. Display user message & add to state
    # This happens within the main script flow, so it will appear after existing messages
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Prepare context for the model
    # Start with history
    full_context = st.session_state.messages[:] # Create a copy

    # Prepend system prompt (with optional file context)
    system_prompt_content = "You are a helpful AI assistant." # Default system prompt
    if st.session_state.file_content:
        system_prompt_content += (
            f"\n\nUse the following text as context if relevant to the user's question:\n\n"
            f"---CONTEXT START---\n{st.session_state.file_content}\n---CONTEXT END---"
        )

    full_context.insert(0, {"role": "system", "content": system_prompt_content})

    # 3. Get and display assistant response (with streaming)
    try:
        # Display assistant response placeholder below the user prompt
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            stream = ollama.chat(
                model=st.session_state.selected_model, # Use the selected model
                messages=full_context,
                stream=True,
            )
            for chunk in stream:
                # Check structure robustly for content
                chunk_content = chunk.get('message', {}).get('content', '')
                if chunk_content:
                    full_response += chunk_content
                    response_placeholder.markdown(full_response + "▌") # Simulate typing cursor

            response_placeholder.markdown(full_response) # Display final response without cursor

        # 4. Add assistant response to state *after* it's fully generated and displayed
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response
        })

        # Optional: Rerun might help ensure layout updates, but often not needed
        # st.rerun()

    except Exception as e:
        st.error(f"Error during chat with Ollama (Model: {st.session_state.selected_model}): {str(e)}")
        # Remove the user message that failed to get a response
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
             st.session_state.messages.pop()
        # Add print statement for debugging server-side errors
        print(f"--- Ollama Chat Exception: {type(e).__name__} - {e} ---")


# --- End of Script ---
# Streamlit automatically re-runs the script on interaction,
# redrawing the chat history from the updated session state.
