import os
import sqlite3
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

def process_pdf(file_path):
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = splitter.split_documents(pages)
    
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    os.makedirs("./data/vector_db", exist_ok=True)
    
    db = Chroma.from_documents(
        documents=docs, 
        embedding=embeddings, 
        persist_directory="./data/vector_db"
    )
    return db

def get_context(query):
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    db = Chroma(persist_directory="./data/vector_db", embedding_function=embeddings)
    results = db.similarity_search(query, k=3)
    return "\n\n".join([d.page_content for d in results])