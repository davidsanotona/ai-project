# 🛡️ David-Dawei Life: Stateful Insurance RAG
**An Edge-AI Solution for Sovereign Data Processing**

This project demonstrates a production-grade **Retrieval-Augmented Generation (RAG)** system designed to interpret complex insurance contracts within the **Republic of Dosu** jurisdiction.

## The Solution
Unlike standard AI chatbots, this system utilizes **Stateful RAG**. It maintains a persistent conversation memory and retrieves context from a local Vector Database, ensuring that sensitive policyholder data (like that of **Ying Zheng**) never leaves the local environment.

### Technical Architecture
* **LLM:** DeepSeek-R1 (1.5B Distilled) via Ollama.
* **Vector Store:** ChromaDB with `nomic-embed-text` embeddings.
* **Orchestration:** LangChain for Conversational Retrieval.
* **Memory:** `ConversationBufferMemory` for multi-turn context retention.



##  Key Features Demonstrated
1.  **Contextual Accuracy:** Correctlty identifies the "Cyber-Stress" rider and territorial exclusions.
2.  **Sovereign Privacy:** 100% local execution—no 3rd party APIs (OpenAI/Anthropic) used.
3.  **Complex Logic:** Handles "Self-Beneficiary" endowment scenarios (Ying Zheng as both insured and beneficiary).

##  Installation
```bash
pip install langchain langchain-community ollama chromadb pypdf pandas
ollama run deepseek-r1:1.5b