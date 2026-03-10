import streamlit as st
import os
from dotenv import load_dotenv
from engine import process_pdf, get_context
from claude_client import ClaudeClient


load_dotenv()

st.set_page_config(page_title="Claude PDF Analyzer")
st.title("Claude PDF Reader")

os.makedirs("data/input_pdfs", exist_ok=True)

uploaded_file = st.file_uploader("Upload a PDF", type="pdf")

if uploaded_file:
    path = os.path.join("data/input_pdfs", uploaded_file.name)
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    with st.spinner("Analyzing PDF..."):
        process_pdf(path)
    st.success("PDF Processed and Indexed!")

query = st.text_input("Ask Claude about the PDF:")
if query:
    if not os.getenv("ANTHROPIC_API_KEY"):
        st.error("Missing API Key! Please check your .env file.")
    else:
        with st.spinner("Claude is thinking..."):
            context = get_context(query)
            client = ClaudeClient()
            answer = client.ask(context, query)
            st.write("### Answer:")
            st.write(answer)