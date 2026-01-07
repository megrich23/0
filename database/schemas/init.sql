-- Initial database schema for Essay System
-- PostgreSQL with pgvector extension

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Sources table
CREATE TABLE sources (
    source_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    base_url VARCHAR(2000),
    allowlisted BOOLEAN DEFAULT TRUE NOT NULL,
    tags TEXT[] DEFAULT '{}',
    fetch_policy JSONB DEFAULT '{}',
    description TEXT,
    document_count INTEGER DEFAULT 0,
    last_fetched_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_sources_allowlisted ON sources(allowlisted) WHERE deleted_at IS NULL;
CREATE INDEX idx_sources_tags ON sources USING GIN(tags);

-- Documents table
CREATE TABLE documents (
    doc_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID NOT NULL REFERENCES sources(source_id),
    retrieved_at TIMESTAMP WITH TIME ZONE NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    raw_content_uri VARCHAR(2000) NOT NULL,
    parsed_text TEXT,
    metadata JSONB DEFAULT '{}',
    processing_status VARCHAR(50) DEFAULT 'pending',
    processing_error TEXT,
    chunk_count INTEGER DEFAULT 0,
    word_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_documents_source ON documents(source_id);
CREATE INDEX idx_documents_hash ON documents(content_hash);
CREATE INDEX idx_documents_source_hash ON documents(source_id, content_hash);

-- Passages table (with vector embeddings)
CREATE TABLE passages (
    passage_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_id UUID NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    char_start INTEGER NOT NULL,
    char_end INTEGER NOT NULL,
    embedding vector(1536),  -- OpenAI embedding dimension
    citability VARCHAR(50) DEFAULT 'quote_ok',
    location_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_passages_doc ON passages(doc_id, chunk_index);
CREATE INDEX idx_passages_embedding ON passages USING ivfflat (embedding vector_cosine_ops);

-- Notes table (Zettelkasten)
CREATE TABLE notes (
    note_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    body TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_notes_tags ON notes USING GIN(tags);

-- Note links (many-to-many)
CREATE TABLE note_links (
    source_note_id UUID REFERENCES notes(note_id) ON DELETE CASCADE,
    target_note_id UUID REFERENCES notes(note_id) ON DELETE CASCADE,
    PRIMARY KEY (source_note_id, target_note_id)
);

-- Note-passage references (many-to-many)
CREATE TABLE note_passages (
    note_id UUID REFERENCES notes(note_id) ON DELETE CASCADE,
    passage_id UUID REFERENCES passages(passage_id) ON DELETE CASCADE,
    PRIMARY KEY (note_id, passage_id)
);

-- Concepts table
CREATE TABLE concepts (
    concept_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL UNIQUE,
    definition TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Concept relations
CREATE TABLE concept_relations (
    relation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_concept_id UUID NOT NULL REFERENCES concepts(concept_id) ON DELETE CASCADE,
    target_concept_id UUID NOT NULL REFERENCES concepts(concept_id) ON DELETE CASCADE,
    relation_type VARCHAR(50) NOT NULL,
    description TEXT
);

CREATE INDEX idx_concept_relations_source ON concept_relations(source_concept_id);
CREATE INDEX idx_concept_relations_target ON concept_relations(target_concept_id);

-- Essay requests table
CREATE TABLE essay_requests (
    request_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt TEXT NOT NULL,
    constraints JSONB DEFAULT '{}',
    audience VARCHAR(200),
    allowed_source_ids JSONB DEFAULT '[]',
    status VARCHAR(50) DEFAULT 'pending',
    current_stage VARCHAR(100),
    progress_percentage INTEGER DEFAULT 0,
    error_message TEXT,
    artifacts JSONB DEFAULT '{}',
    quality_metrics JSONB DEFAULT '{}',
    final_essay TEXT,
    bibliography TEXT,
    uncertainties JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_essay_requests_status ON essay_requests(status);
CREATE INDEX idx_essay_requests_created ON essay_requests(created_at DESC);

-- Digest issues table
CREATE TABLE digest_issues (
    issue_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    tags TEXT[] DEFAULT '{}',
    title VARCHAR(500) NOT NULL,
    summary TEXT NOT NULL,
    clusters JSONB DEFAULT '[]',
    highlights JSONB DEFAULT '[]',
    emerging_themes JSONB DEFAULT '[]',
    trend_stats JSONB DEFAULT '{}',
    notable_quotes JSONB DEFAULT '[]',
    document_count INTEGER DEFAULT 0,
    source_count INTEGER DEFAULT 0,
    published BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_digest_period ON digest_issues(period_start, period_end);
CREATE INDEX idx_digest_published ON digest_issues(published);

-- Digest clusters table
CREATE TABLE digest_clusters (
    cluster_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    issue_id UUID NOT NULL REFERENCES digest_issues(issue_id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    document_ids JSONB DEFAULT '[]',
    keywords TEXT[] DEFAULT '{}',
    entities JSONB DEFAULT '{}',
    centrality_score FLOAT DEFAULT 0.0
);

CREATE INDEX idx_digest_clusters_issue ON digest_clusters(issue_id);

-- Culture watch sources table
CREATE TABLE culture_watch_sources (
    cw_source_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
    fetch_frequency_hours INTEGER DEFAULT 24,
    last_successful_fetch TIMESTAMP WITH TIME ZONE,
    last_error TEXT,
    total_items_fetched INTEGER DEFAULT 0,
    items_this_week INTEGER DEFAULT 0,
    items_this_month INTEGER DEFAULT 0,
    consecutive_errors INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_cw_sources_active ON culture_watch_sources(is_active);

-- Update triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_sources_updated_at BEFORE UPDATE ON sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_passages_updated_at BEFORE UPDATE ON passages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notes_updated_at BEFORE UPDATE ON notes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_concepts_updated_at BEFORE UPDATE ON concepts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_essay_requests_updated_at BEFORE UPDATE ON essay_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_digest_issues_updated_at BEFORE UPDATE ON digest_issues
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cw_sources_updated_at BEFORE UPDATE ON culture_watch_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
