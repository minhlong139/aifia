-- ==============================================================
-- AIFIA optional vector search layer
-- Apply this only if the live Supabase project does not already
-- have an equivalent indexed document table/RPC.
-- ==============================================================

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS ai_documents (
    id          BIGSERIAL PRIMARY KEY,
    symbol      VARCHAR(20),
    title       TEXT,
    content     TEXT NOT NULL,
    metadata    JSONB DEFAULT '{}'::jsonb,
    embedding   VECTOR(1536) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_documents_symbol
    ON ai_documents(symbol);

CREATE INDEX IF NOT EXISTS idx_ai_documents_metadata
    ON ai_documents USING GIN(metadata);

-- HNSW gives fast approximate nearest-neighbor retrieval for chat.
-- vector_cosine_ops matches OpenAI embedding cosine similarity.
CREATE INDEX IF NOT EXISTS idx_ai_documents_embedding_hnsw
    ON ai_documents USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(1536),
    match_threshold DOUBLE PRECISION DEFAULT 0.7,
    match_count INT DEFAULT 8,
    filter JSONB DEFAULT '{}'::jsonb
)
RETURNS TABLE (
    id BIGINT,
    symbol VARCHAR(20),
    title TEXT,
    content TEXT,
    metadata JSONB,
    similarity DOUBLE PRECISION
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.symbol,
        d.title,
        d.content,
        d.metadata,
        1 - (d.embedding <=> query_embedding) AS similarity
    FROM ai_documents d
    WHERE
        (filter = '{}'::jsonb OR d.metadata @> filter OR (filter ? 'symbol' AND d.symbol = filter->>'symbol'))
        AND 1 - (d.embedding <=> query_embedding) >= match_threshold
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
