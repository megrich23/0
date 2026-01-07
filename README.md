# Multi-Agent Essay Writer + Philosophy Reader + Culture Watcher

A sophisticated multi-agent system for producing high-quality essays, absorbing philosophical texts, and monitoring cultural scenes with full provenance tracking and citation support.

## Overview

This system provides three core capabilities:

1. **Essay Studio**: Generate well-structured, source-grounded essays from a single prompt using a multi-agent workflow (planning → research → drafting → critique → revision)

2. **Philosophy Library**: Ingest and absorb philosophical texts through layered summaries, argument extraction, concept graphs, and Zettelkasten-style notes

3. **Culture Watch**: Monitor specific cultural scenes, outlets, and literary magazines with automated digests and trend tracking

## Key Features

- **Source-Bounded Writing**: Only uses explicitly allowlisted sources
- **Full Provenance**: Every claim traced to specific passages
- **Multi-Agent Architecture**: Specialized agents for planning, writing, critique, and curation
- **Pluggable LLM Support**: Works with Kimi 2, OpenAI, Anthropic, or local models
- **Quality Controls**: Citation coverage, specificity scoring, cliché detection
- **Ethical Design**: Transparent authorship, no deception tools

## Architecture

```
┌──────────────────────────┐
│  Orchestrator / Router    │
│  (multi-agent runtime)     │
└───────┬─────────┬────────┘
        │         │
┌───────▼─┐   ┌──▼─────────┐
│  Agents   │   │ Tool Layer │
│ (Writer,  │   │ (Fetch,    │
│ Critic,   │   │ Parse,     │
│ Curator…) │   │ Search KB) │
└─────┬─────┘   └──┬─────────┘
      │            │
┌─────▼────────────▼─────┐
│ Knowledge & Provenance  │
│ - Document store        │
│ - Vector index          │
│ - Concept graph         │
│ - Citations store       │
└──────────┬──────────────┘
           │
   ┌───────▼────────┐
   │ UI + Exports    │
   │ (web/app/cli)   │
   └─────────────────┘
```

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with pgvector
- **Vector Store**: pgvector / Pinecone
- **Object Storage**: S3-compatible (MinIO/S3)
- **Queue**: Redis + Celery
- **Scheduler**: APScheduler

### Frontend
- **Framework**: Next.js 14+ (React)
- **UI**: Tailwind CSS + shadcn/ui
- **State**: Zustand / TanStack Query

### Parsing & Processing
- **Text Extraction**: unstructured, trafilatura, pdfminer
- **Embeddings**: sentence-transformers / OpenAI
- **Graph**: NetworkX / Neo4j (optional)

## Project Structure

```
├── backend/
│   ├── agents/           # Agent implementations
│   ├── api/              # FastAPI routes
│   ├── core/             # Core orchestrator
│   ├── models/           # Data models (Pydantic)
│   ├── services/         # Business logic
│   ├── tools/            # Agent tools
│   └── utils/            # Utilities
├── frontend/
│   ├── components/       # React components
│   ├── pages/            # Next.js pages
│   ├── lib/              # Client utilities
│   └── styles/           # CSS/Tailwind
├── database/
│   ├── migrations/       # Alembic migrations
│   └── schemas/          # SQL schemas
├── docs/                 # Documentation
├── config/               # Configuration files
└── tests/                # Test suites
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ with pgvector extension
- Redis 7+
- (Optional) S3-compatible storage

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. **Set up Python environment**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up frontend**
   ```bash
   cd frontend
   npm install
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   cd backend
   alembic upgrade head
   ```

6. **Start services**

   Terminal 1 - Backend:
   ```bash
   cd backend
   uvicorn api.main:app --reload
   ```

   Terminal 2 - Frontend:
   ```bash
   cd frontend
   npm run dev
   ```

   Terminal 3 - Worker:
   ```bash
   cd backend
   celery -A core.worker worker --loglevel=info
   ```

## Usage

### Essay Studio

```python
from backend.api.client import EssayClient

client = EssayClient()

# Request an essay
response = client.create_essay(
    prompt="Explore Heidegger's concept of Being-toward-death in relation to contemporary anxiety culture",
    constraints={
        "wordcount": 2000,
        "tone": "academic",
        "citation_style": "MLA",
        "mode": "strict"  # Only use allowlisted sources
    },
    allowed_sources=["heidegger_being_and_time.pdf"]
)

# Get the completed essay
essay = client.get_essay(response.request_id)
print(essay.draft)
print(essay.bibliography)
```

### Philosophy Library

```python
# Upload and process a text
library = PhilosophyLibrary()
result = library.ingest_text(
    file_path="kant_critique.pdf",
    tags=["kant", "epistemology", "critique"]
)

# Get layered summaries
summaries = library.get_summaries(result.doc_id)
print(summaries.three_sentence)
print(summaries.one_page)

# Export flashcards
flashcards = library.export_flashcards(result.doc_id, format="anki")
```

### Culture Watch

```python
# Configure sources
watcher = CultureWatcher()
watcher.add_source(
    url="https://gasda.net/feed",
    type="rss",
    tags=["dimes_square", "criticism"]
)

# Generate digest
digest = watcher.generate_digest(
    period_days=7,
    tags=["dimes_square"]
)
print(digest.highlights)
print(digest.emerging_themes)
```

## Operating Modes

### Mode A: Source-Only (Strict)
- Only references user-uploaded documents and allowlisted URLs
- Maximum provenance and control

### Mode B: Open Research
- Allows web search and broader context
- Still enforces citations and uncertainty labeling

### Mode C: Culture Watch
- Scheduled ingestion + digest generation
- Uses allowlist + optional APIs

## Quality Controls

The system enforces quality through:

- **Thesis discipline**: One controlling idea throughout
- **Argument mapping**: Claims → evidence → warrants
- **Evidence requirements**: No big claims without supporting quotes
- **Concrete anchors**: Names, dates, passages, examples
- **Voice constraints**: Sentence-length targets, forbidden phrases
- **Revision loops**: Multiple critique passes (structure + style)
- **Provenance audit**: Every paragraph cited or labeled speculative

## API Documentation

Full API documentation available at `http://localhost:8000/docs` when running the backend.

Key endpoints:

- `POST /api/v1/essays` - Create essay request
- `GET /api/v1/essays/{id}` - Get essay status/result
- `POST /api/v1/library/ingest` - Upload document
- `GET /api/v1/library/notes` - Browse notes
- `POST /api/v1/watch/sources` - Add culture watch source
- `GET /api/v1/watch/digest` - Get latest digest

## Configuration

### LLM Providers

Configure in `config/providers.yaml`:

```yaml
providers:
  default: openai

  openai:
    api_key: ${OPENAI_API_KEY}
    model: gpt-4-turbo-preview

  kimi:
    api_key: ${KIMI_API_KEY}
    model: kimi-2
    base_url: https://api.kimi.ai/v1

  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    model: claude-3-opus-20240229

# Assign models to agents
agent_models:
  planner: openai
  writer: kimi
  critic: anthropic
  curator: openai
```

### Style Profiles

Create custom voice profiles in `config/styles/`:

```yaml
# academic.yaml
name: "Academic"
sentence_length:
  min: 15
  max: 35
  target_avg: 22
forbidden_phrases:
  - "In today's world"
  - "Throughout history"
  - "It is important to note"
preferred_transitions:
  - "Moreover"
  - "Conversely"
  - "In contrast"
rhetorical_devices:
  - "rhetorical_question"
  - "parallel_structure"
citation_density: 0.7  # 70% of paragraphs must have citations
```

## Testing

```bash
# Run all tests
pytest

# Run specific suite
pytest tests/unit/agents/
pytest tests/integration/essay_workflow/

# Run with coverage
pytest --cov=backend --cov-report=html
```

## Development

See [CLAUDE.md](./CLAUDE.md) for AI assistant guidelines.

See [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) for detailed architecture documentation.

See [docs/AGENTS.md](./docs/AGENTS.md) for agent design patterns.

## Ethical Guidelines

This system is designed for:
- ✅ High-quality drafting with human review
- ✅ Research assistance with full citations
- ✅ Knowledge organization and synthesis
- ✅ Cultural scene monitoring

This system is NOT designed for:
- ❌ Evading AI detection tools
- ❌ Plagiarism or deception about authorship
- ❌ Bypassing paywalls or violating ToS
- ❌ Presenting AI output as human expertise without review

All outputs should be reviewed by humans and properly attributed.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for contribution guidelines.

## License

[License TBD]

## Roadmap

### Milestone 1: Essay Studio (Strict Mode) ✓
- [x] Upload docs
- [x] Basic RAG
- [x] Planner → Writer → Critic → Audit pipeline
- [x] Export with citations

### Milestone 2: Philosophy Library
- [ ] Layered summaries + zettels + concept graph
- [ ] Flashcards export

### Milestone 3: Culture Watch
- [ ] Allowlist sources + RSS ingestion
- [ ] Weekly digest + clustering + dedupe

### Milestone 4: Multi-model Adapter
- [ ] Kimi 2 adapter
- [ ] Model selection per agent

## Support

For questions or issues:
- GitHub Issues: [Link TBD]
- Documentation: [docs/](./docs/)
- Design Doc: See repository root

---

**Built with**: FastAPI, Next.js, PostgreSQL, pgvector, and modern LLMs
