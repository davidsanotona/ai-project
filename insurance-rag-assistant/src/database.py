import os
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings

class VectorStoreManager:
    def __init__(self, db_dir="./chroma_db"):
        self.db_dir = db_dir
        self.embeddings = OllamaEmbeddings(model="nomic-embed-text")

    def create_database(self, file_path):
        # Support for both Text and PDF
        if file_path.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path)
            
        documents = loader.load()
        
        # Optimized chunking for 3-page documents
        # 800 chars is enough to capture full clauses like '2.2 Conditions for Claim'
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800, 
            chunk_overlap=100
        )
        chunks = text_splitter.split_documents(documents)
        
        # Create and persist the database
        vector_db = Chroma.from_documents(
            documents=chunks, 
            embedding=self.embeddings,
            persist_directory=self.db_dir
        )
        print(f"Database created and saved to {self.db_dir}")
        return vector_db

    def load_database(self):
        if os.path.exists(self.db_dir):
            return Chroma(
                persist_directory=self.db_dir, 
                embedding_function=self.embeddings
            )
        return None