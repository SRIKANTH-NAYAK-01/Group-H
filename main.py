# app/ui/streamlit_app.py
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
# import os
from pathlib import Path

# Import KB/RAG module (mock for now)
from app.chatbot.chain import ask_doctor_question  # Replace with your KB function

# =========================
# Streamlit App Config
# =========================
st.set_page_config(
    page_title="Clinical OCT Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# Sidebar - Upload Image
# =========================
with st.sidebar.expander("Upload OCT Image (Optional)"):
    uploaded_file = st.file_uploader(
        "Choose OCT image",
        type=["png", "jpg", "jpeg", "tiff"]
    )
    if uploaded_file:
        upload_path = Path("app/assets/uploads") / uploaded_file.name
        with open(upload_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"Uploaded: {uploaded_file.name}")
        st.image(upload_path, caption="Uploaded OCT Image", use_column_width=True)

# =========================
# Sidebar - Disease (manual entry for now)
# =========================
st.sidebar.markdown("---")
disease_name = st.sidebar.text_input("Enter Disease Name (for demo)")

# =========================
# Main Chat Interface
# =========================
st.title("🩺 Clinical OCT Assistant Chat")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display chat history
for chat in st.session_state.chat_history:
    if chat["role"] == "user":
        st.markdown(f"**Doctor:** {chat['content']}")
    else:
        st.markdown(f"**Assistant:** {chat['content']}")

# User input
user_input = st.text_input("Type your question here...")

if st.button("Send") and user_input:
    # Append doctor message
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    # For demo, use disease_name if available
    if disease_name:
        question_to_ask = f"Disease: {disease_name}. Question: {user_input}"
    else:
        question_to_ask = user_input

    # Call RAG assistant (mock / actual)
    response = ask_doctor_question(disease_name, question_to_ask)
    st.session_state.chat_history.append({"role": "assistant", "content": response})
    st.experimental_rerun()

# =========================
# Footer / Instructions
# =========================
st.sidebar.markdown("---")
st.sidebar.info(
    "1. Upload OCT image to associate with chat.\n"
    "2. Enter disease manually for demo purposes.\n"
    "3. Chat with the assistant to get recommendations.\n"
    "4. Final PDF report generation will come after approval flow integration."
)
