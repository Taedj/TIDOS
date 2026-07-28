# TIDOS Plugin: AI & LLM Pipelines (v3.0)

## 1. Detection Rules
- **Dependencies**: `openai`, `anthropic`, `google-generativeai`, `langchain`, `llamaindex`
- **Signature Directories**: `prompts/`, `embeddings/`, `rag/`

## 2. Initialization Steps
- Verify API key environment variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_AI_API_KEY`).
- Validate vector database connection (Pinecone, Weaviate, pgvector, ChromaDB).

## 3. Documentation to Generate
- `AI_ARCHITECTURE.md`: Document prompt templates, embedding pipeline, RAG retrieval flow, and model selection.

## 4. Best Practices
- Version control prompt templates as discrete files, not inline strings.
- Implement structured output parsing (JSON mode / function calling) over free-text extraction.

## 5. Coding Standards
- Isolate LLM API calls behind typed service interfaces for testability and provider swapping.
- Log token usage, latency, and model version per API invocation for cost tracking.

## 6. Review & Quality Rules
- Validate zero hardcoded API keys in source files.
- Verify retry logic with exponential backoff on rate-limited API calls.

## 7. Research Topics
- MCP (Model Context Protocol) server integrations, multi-agent orchestration, structured output schemas.
