# TIDOS Plugin: AI Systems, LLM Pipelines & RAG

## 1. Detection Rules
- **Signature Files**: `langchain`, `llama-index`, `openai`, `google-generativeai`, `chromadb`, `pinecone`
- **Dependencies**: `ai`, `@google/genai`, `ollama`

## 2. Initialization Steps
- Verify API key environment variables (`OPENAI_API_KEY`, `GEMINI_API_KEY`).
- Check local or remote vector database connection endpoints.

## 3. Documentation to Generate
- `AI_PIPELINE_SPEC.md`: Document prompt architecture, model parameters, context window limits, and fallback strategies.

## 4. Best Practices
- Isolate prompt templates inside dedicated text files or templates directory (`.tidos/templates/`).
- Implement streaming responses for long generation outputs to minimize user-perceived latency.

## 5. Coding Standards
- Sanitize user input strings before embedding into prompts to prevent prompt injection.
- Implement structured output validation (JSON schema enforcement / Pydantic / Zod).

## 6. Review & Quality Rules
- Validate presence of fallback models or retries with exponential backoff on rate-limit errors.
- Check token count calculation and context window bounding guards.

## 7. Research Topics
- Local LLM inference (Ollama/llama.cpp), Function calling & Tool Use reliability, Hybrid keyword/semantic RAG search.
