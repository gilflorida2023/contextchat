# DeepSeek Chat with File Context

This is a simple Streamlit application that provides a chat interface using the DeepSeek model from Ollama, with the ability to provide context to the model by uploading a text file.

## Features

* Chat with the DeepSeek model.
* Upload a text file to provide context for the chat.
* Displays chat history.

## Prerequisites

* Python 3.6 or higher
* Ollama installed and running with the `deepseek-r1:32b` (or `deepseek-r1:1.5b`) model pulled. You can pull the model using the command: `ollama pull deepseek-r1:32b` (or `ollama pull deepseek-r1:1.5b`).

## Installation

1.  Clone this repository (or download the `app.py` and `requirements.txt` files).
2.  Navigate to the project directory in your terminal.
3.  Create a virtual environment and activate it:

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

4.  Install the required dependencies:

    ```bash
    pip install --timeout=60 -r requirements.txt
    ```

    *(Note: The `--timeout=60` is included to prevent potential timeouts during installation)*

## Running the Application

1.  Make sure your Ollama instance is running and the `deepseek-r1:32b` (or `deepseek-r1:1.5b`) model is available.
2.  Activate your virtual environment if you haven't already:

    ```bash
    source venv/bin/activate
    ```

3.  Run the Streamlit application:

    ```bash
    streamlit run app.py
    ```

This will open the application in your web browser.

## How to Use

1.  **Upload a text file:** Use the file uploader to select a text file. The content of this file will be used as context for the chat.
2.  **Ask questions:** Once the file content is loaded, you can type your questions in the chat input box at the bottom of the page.
3.  **Chat:** The DeepSeek model will respond to your questions, using the uploaded file content as a primary source of information.

## app.py Documentation

The `app.py` file contains the source code for the Streamlit application.

* It initializes the Streamlit application and sets the title.
* It uses `st.session_state` to maintain the chat history and the content of the uploaded file.
* The `st.file_uploader` allows users to upload a text file. The content is read and stored in `st.session_state.file_content`.
* Existing chat messages from `st.session_state.messages` are displayed.
* The `st.chat_input` allows users to type new messages.
* When a user submits a message, it's added to the session state, and the full context (file content + chat history) is sent to the Ollama API using the `ollama.chat` function with the specified model (`deepseek-r1:32b` or `deepseek-r1:1.5b`).
* The model's response is streamed and displayed in the chat interface.
* The final assistant response is added to the `st.session_state.messages`.
* Error handling is included for issues with file decoding and communication with Ollama.
