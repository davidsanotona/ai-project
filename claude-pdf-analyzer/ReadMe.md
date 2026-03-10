# Claude PDF Analyzer (RAG)

A Retrieval-Augmented Generation (RAG) application that allows you to upload PDFs and have intelligent conversations about their content using Claude 4.6 and ChromaDB.

---

## Quick Start

### 1. Environment Setup

Create a dedicated Conda environment to avoid library conflicts (highly recommended for Windows users):
```bash
conda create -n claude_311 python=3.11 -y
conda activate claude_311
```

### 2. Install Dependencies

Install the required 2026-standard libraries:
```bash
pip install streamlit langchain-chroma langchain-anthropic langchain-community langchain-huggingface pypdf chromadb python-dotenv
```

### 3. Configuration

Create a `.env` file in the root directory and add your Anthropic API key:
```env
ANTHROPIC_API_KEY=your_sk_key_here
```

### 4. Run the Application
```bash
python -m streamlit run app/main.py
```

---

## Project Structure
```
├── app/
│   ├── main.py           # Streamlit frontend and UI logic
│   ├── engine.py         # RAG logic (PDF loading, splitting, vector storage)
│   └── claude_client.py  # API wrapper for Claude 4.6
└── data/                 # Local storage for PDFs and Chroma vector database
```

---

## How It Works

1. **Ingestion** — PDFs are parsed using `PyPDFLoader` and split into 1000-character chunks.
2. **Vectorization** — Chunks are embedded using `all-MiniLM-L6-v2`, running locally on your CPU.
3. **Storage** — Embeddings are stored in a local ChromaDB instance.
4. **Retrieval** — Questions are matched against the 3 most relevant chunks from your PDF.
5. **Generation** — Relevant snippets and your question are sent to Claude 4.6 for a precise, context-aware answer.

---

## Troubleshooting

| Issue | Fix |
|---|---|
| Wrong Python version | Use Python 3.11+ |
| Model not found error | Use `claude-sonnet-4-6` as the model ID |
| SQLite errors on Windows | Remove any `pysqlite3-binary` references and use the built-in `sqlite3` module |