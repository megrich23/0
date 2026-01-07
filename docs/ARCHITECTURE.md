# Architecture Overview

This document provides a high-level overview of the system architecture.

## System Components

### 1. Multi-Agent System

The core of the application is a multi-agent system where specialized agents collaborate to complete complex tasks.

**Agent Types:**
- **PlannerAgent**: Creates outlines and argument maps
- **ResearchAgent**: Retrieves evidence from the knowledge base
- **WriterAgent**: Drafts essay sections
- **CriticAgent**: Evaluates structural and stylistic quality
- **FactCheckerAgent**: Verifies citations and provenance
- **CuratorAgent**: Creates digests from cultural content
- **PhilosophyTutorAgent**: Processes philosophical texts

### 2. LLM Provider Layer

A provider abstraction allows swapping between different LLM backends:

- **OpenAI** (GPT-4, GPT-3.5)
- **Anthropic** (Claude)
- **Kimi 2** (Moonshot AI)
- **Local models** (via compatible APIs)

Each agent can use a different provider, optimizing for cost vs. quality.

### 3. Knowledge Base

**Components:**
- **Document Store**: PostgreSQL with metadata
- **Vector Store**: pgvector for semantic search
- **Concept Graph**: Relationships between philosophical concepts
- **Note System**: Zettelkasten-style linked notes

**Flow:**
1. Documents ingested → parsed → chunked
2. Chunks embedded → stored with vectors
3. Semantic search retrieves relevant passages
4. Citations link back to original sources

### 4. Orchestrator

The orchestrator manages multi-step workflows:

**Features:**
- Dependency resolution (steps execute in order)
- Parallel execution (independent steps run concurrently)
- Artifact passing (outputs flow between steps)
- Error handling and retries
- Progress tracking

**Example Workflow (Essay Generation):**
```
Plan → Research → Draft → Critique → Revise → Fact-Check
```

### 5. API Layer (FastAPI)

REST API provides access to all functionality:

**Endpoints:**
- `/api/v1/essays` - Essay creation and retrieval
- `/api/v1/library` - Philosophy document management
- `/api/v1/watch` - Culture watch configuration
- `/api/v1/sources` - Source allowlist management

### 6. Frontend (Next.js)

Three main interfaces:

1. **Essay Studio**: Request essays, view outlines, review drafts
2. **Philosophy Library**: Upload texts, browse notes, export flashcards
3. **Culture Watch**: Configure sources, view digests, track trends

## Data Flow

### Essay Generation Flow

```
User Prompt
    ↓
Planner Agent → Creates outline
    ↓
Research Agent → Finds evidence for claims
    ↓
Writer Agent → Drafts sections with citations
    ↓
Critic Agents → Identify structural/style issues
    ↓
Writer Agent → Revises based on critique
    ↓
Fact Checker → Verifies citations, flags unsupported claims
    ↓
Final Essay + Bibliography + Uncertainties
```

### Philosophy Reading Flow

```
Upload PDF/Text
    ↓
Parse & Chunk
    ↓
Generate Embeddings
    ↓
Philosophy Tutor Agent:
    - Layered summaries
    - Argument extraction
    - Objection generation
    - Concept graph updates
    - Note creation
    - Flashcard generation
    ↓
Searchable Knowledge Base + Study Materials
```

### Culture Watch Flow

```
Configure Allowlist (RSS, newsletters, etc.)
    ↓
Scheduled Fetching
    ↓
Parse & Deduplicate
    ↓
Curator Agent:
    - Cluster related items
    - Extract themes
    - Track entities
    - Identify trends
    ↓
Weekly Digest
```

## Quality Controls

### Provenance Tracking

Every paragraph in generated essays:
- Has citation(s) to source passages, OR
- Is labeled [SPECULATIVE]

### Source Constraints

**Strict Mode** (default):
- Only use explicitly allowlisted sources
- No web search or external references
- Full audit trail

**Open Mode** (optional):
- Allow web search
- Still requires citations
- Labels uncertainty

### Quality Metrics

Automatically computed:
- **Citation coverage**: % of paragraphs with citations
- **Specificity score**: Density of concrete nouns, names, examples
- **Cliché count**: Occurrences of forbidden filler phrases
- **Outline alignment**: Draft matches intended structure

## Scalability Considerations

### Current Architecture
- Monolithic backend (FastAPI)
- Single PostgreSQL database
- Celery workers for async tasks

### Future Scaling Options
- **Horizontal scaling**: Multiple API instances behind load balancer
- **Worker pools**: Dedicated workers per agent type
- **Separate vector store**: Dedicated Milvus or Pinecone instance
- **Caching layer**: Redis for frequently accessed passages
- **CDN**: Static assets and document storage

## Security

### Authentication & Authorization
- API key authentication for programmatic access
- OAuth for web interface
- Source-based permissions (users can only access their sources)

### Data Protection
- All API keys stored as environment variables
- Source documents encrypted at rest
- User data isolated (multi-tenancy)

### Rate Limiting
- Per-user request limits
- Per-provider token limits
- Queuing for expensive operations

## Configuration

### Environment-Based Config
- `.env` files for local development
- Environment variables for production
- `config/providers.yaml` for LLM configuration

### Feature Flags
- Strict mode vs. open mode
- Web search enable/disable
- Experimental agents

## Deployment

### Development
```bash
# Backend
cd backend && uvicorn api.main:app --reload

# Frontend
cd frontend && npm run dev

# Worker
celery -A core.worker worker
```

### Production
- **Backend**: Gunicorn + Uvicorn workers
- **Frontend**: Next.js static export or SSR
- **Database**: Managed PostgreSQL (AWS RDS, etc.)
- **Queue**: Redis cluster
- **Storage**: S3-compatible object storage

## Monitoring & Observability

### Metrics
- Request latency
- Token usage per agent/provider
- Essay quality scores
- Error rates

### Logging
- Structured JSON logs
- Agent execution traces
- Provider API calls

### Alerts
- Failed essay generations
- Provider API failures
- Database connection issues
- Quality score drops

---

**Version**: 1.0
**Last Updated**: 2026-01-07
