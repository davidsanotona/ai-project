import os
from langchain_community.llms import Ollama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain.chains.retrieval import create_retrieval_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.chains.combine_documents import create_stuff_documents_chain

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

class InsuranceAssistant:
    def __init__(self, data_path):
        self.llm = Ollama(model="deepseek-r1:1.5b")
        self.embeddings = OllamaEmbeddings(model="nomic-embed-text")
        
        # 1. Load Data
        loader = PyPDFLoader(data_path) if data_path.endswith('.pdf') else TextLoader(data_path)
        docs = loader.load()
        
        # 2. Split and Store
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = splitter.split_documents(docs)
        self.vector_db = Chroma.from_documents(documents=chunks, embedding=self.embeddings)
        self.retriever = self.vector_db.as_retriever()

        # 3. Contextualize Question (Memory Logic)
        contextualize_q_system_prompt = "Given a chat history and the latest user question, formulate a standalone question."
        contextualize_q_prompt = ChatPromptTemplate.from_messages([
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])
        
        history_aware_retriever = create_history_aware_retriever(
            self.llm, self.retriever, contextualize_q_prompt
        )

        # 4. Answer Logic
        system_prompt = "You are an insurance assistant. Use the context to answer. Context: {context}"
        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])
        
        question_answer_chain = create_stuff_documents_chain(self.llm, qa_prompt)
        self.rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
        
        # 5. Local Memory Storage
        self.chat_history = []

    def ask(self, question):
        # Invoke the modern chain
        response = self.rag_chain.invoke({"input": question, "chat_history": self.chat_history})
        
        # Update memory
        self.chat_history.extend([("human", question), ("ai", response["answer"])])
        
        return response["answer"]