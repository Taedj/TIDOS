# TIDOS + AI Application Integration Example

## Project Type
AI/LLM application with prompt engineering, RAG, and model orchestration.

## TIDOS Connection

```bash
cd ai_app
git submodule add https://github.com/tidjani/TIDOS.git .tidos
```

## Plugins Mounted

- `plugins/ai.md` - AI pipelines specification
- `plugins/python.md` - Python services (if applicable)
- `plugins/nodejs.md` - Node.js services (if applicable)

## Key Rules Applied

- Prompt template management and versioning
- RAG pipeline architecture (ingestion -> embedding -> retrieval -> generation)
- Model fallback strategy and cost optimization
- Token usage tracking and budgeting
- Evaluation framework for output quality

## Architecture

```
data/          -> Documents, embeddings, vector store
services/      -> LLM clients, embedding services, retrieval
prompts/       -> Prompt templates with variables
evaluation/    -> Quality metrics and test suites
```

## Startup Report

```
Detected Stack: Python + OpenAI + ChromaDB
Active Plugins: ai.md, python.md
```
