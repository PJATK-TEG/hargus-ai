# AI Candidate Analyzer - Hargus AI

## What We'll Build
An AI-powered candidate analysis system that uses RAG, GraphRAG, and a multi-agent MCP architecture to holistically profile job candidates. We will solve a real HR challenge: aggregating and reasoning over heterogeneous candidate data — CVs, interview transcripts, and publicly available background information — to produce structured, explainable insights.

## Project Overview

### Problem
Hiring teams struggle to build a complete picture of a candidate because:
- Data is scattered across multiple formats (PDFs, transcripts, web sources)
- Manual review of all documents doesn't scale across many applicants
- Answering cross-document questions ("Did the candidate mention Python in both the CV and interview?") requires reasoning across sources
- Sensitive personal data demands careful security controls

### Solution
Build an AI Candidate Analyzer that:
- Ingests CVs (PDF), interview transcripts (text/audio), and public background data
- Builds a knowledge graph linking candidates, skills, experience, and statements
- Exposes a multi-agent interface where specialized agents handle different data sources via MCP tools
- Answers natural language queries with cited, explainable answers
- Runs fully locally using Ollama

## Project Phases

### Phase 1: Foundation
**Goal**: Environment setup and data ingestion pipeline

**Tasks:**
- Set up Neo4j with Docker Compose
- Configure Ollama with a suitable local model (e.g., `llama3`, `mistral`)
- Generate or collect sample candidate data: 20+ CVs (PDF), 20+ interview transcripts, mock public profile summaries
- Design the knowledge graph schema (Candidate, Skill, Experience, Statement, Source nodes)

### Phase 2: RAG & GraphRAG Pipeline
**Goal**: Build the core retrieval and graph reasoning engine

**Tasks:**
- Implement naive RAG baseline: chunk documents, embed with Ollama, store in vector store (Chroma or FAISS)
- Build GraphRAG pipeline: extract entities and relationships from documents with an LLM, populate Neo4j
- Implement LangChain graph query chain (`GraphCypherQAChain`) for structured retrieval
- Cross-source linking: connect CV skills to mentions in interview transcripts and background data

### Phase 3: Multi-Agent MCP Architecture 
**Goal**: Build specialized agents and a central orchestrator

**Tasks:**
- Define MCP tools/skills for each data source:
  - `CVAgent`: retrieves and summarizes CV content
  - `InterviewAgent`: extracts key statements and behavioral signals from transcripts
  - `BackgroundAgent`: queries public data summaries and flags inconsistencies
- Build a `CandidateOrchestratorAgent` that routes queries to the appropriate sub-agents and synthesizes results
- Expose agents as MCP-compatible servers
- Implement a natural language interface

**Key Queries to Support:**
- "Summarize this candidate's technical skills based on all available data."
- "Are there any inconsistencies between the CV and interview transcript?"
- "What soft skills did the candidate demonstrate in the interview?"
- "Flag any concerns from the background check data."
- "Compare candidates A and B for the Senior Backend Engineer role."

### Phase 4: Security, Testing & Evaluation
**Goal**: Harden the system and validate correctness

**Tasks:**
- Implement input sanitization to prevent prompt injection in user queries and ingested documents
- Add access control layer: restrict which agents/tools can access which data categories
- Anonymize PII in logs and intermediate outputs
- Write pytest suite covering: ingestion pipeline, graph queries, agent routing, security controls
- Performance benchmarking: latency per query type, GraphRAG vs. RAG accuracy on a labeled eval set
- Final documentation and demonstration video

## Success Criteria

### Minimum Requirements
- [ ] Ingest and build a knowledge graph from 20+ candidates (CV + transcript + background)
- [ ] Answer 10 cross-document candidate queries correctly via GraphRAG
- [ ] Demonstrate GraphRAG superiority over naive RAG on multi-source questions
- [ ] Orchestrator correctly routes queries to specialized agents
- [ ] All inference runs locally via Ollama (no external LLM API required)
- [ ] Test suite passes with >80% coverage
- [ ] Security controls documented and validated

### Advanced Features
- [ ] Audio interview transcript ingestion (Whisper via Ollama)
- [ ] Candidate comparison and ranking interface
- [ ] Web dashboard with graph visualization (Neo4j Bloom or custom)
- [ ] Automated red-flag detection agent
- [ ] Real-time document ingestion via file watcher

## Business Scenarios to Solve
1. **Skill Verification**: "Does the candidate's interview confirm the Python expertise listed on their CV?"
2. **Red Flag Detection**: "Are there any inconsistencies or gaps across all data sources for this candidate?"
3. **Behavioral Analysis**: "What leadership examples did the candidate give in their interview?"
4. **Comparative Ranking**: "Rank these three candidates for a senior DevOps role based on all available data."
5. **Background Reconciliation**: "Does the candidate's claimed work history align with publicly available information?"

## Getting Started

### Tech Stack
- **LLM Runtime**: Ollama (local, no external API keys required)
- **Recommended Models**: `llama3`, `mistral`, or `nomic-embed-text` for embeddings
- **Graph Database**: Neo4j (Docker)
- **RAG / Graph Framework**: LangChain (`langchain-neo4j`, `GraphCypherQAChain`)
- **Vector Store**: Chroma or FAISS
- **Agent Protocol**: MCP (Model Context Protocol)
- **Frontend**: Streamlit (simple) or React (advanced)
- **Testing**: pytest + pytest-cov
- **Containerization**: Docker Compose

### Possible Extension Areas
Extend the base implementation to handle:
- Multi-modal input (audio transcripts via Whisper)
- Structured scoring rubrics per job role
- Explainability layer: cite which document supports each answer
- Differential privacy for candidate data storage

## Security Requirements
Because this system handles sensitive personal data, the following controls are mandatory:

- **Prompt Injection Prevention**: Sanitize all user inputs and ingested document content before passing to LLMs
- **PII Handling**: Redact or hash personally identifiable information in logs and vector store metadata
- **Access Control**: Agents must only access data sources within their defined scope
- **Audit Logging**: All queries and agent actions must be logged with timestamps (no sensitive data in logs)
- **Data Minimization**: Only store and process data that is necessary for the query at hand
