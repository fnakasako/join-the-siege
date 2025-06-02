-- Database initialization script for document classifier
-- This script sets up the necessary tables for tracking classifications and metrics

-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table for storing classification results (optional - for analytics)
CREATE TABLE IF NOT EXISTS classifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    industry VARCHAR(50) NOT NULL,
    classification VARCHAR(100) NOT NULL,
    confidence DECIMAL(3,2) NOT NULL,
    processing_time DECIMAL(8,3),
    cached BOOLEAN DEFAULT FALSE,
    worker_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_classifications_hash_industry ON classifications(file_hash, industry);
CREATE INDEX IF NOT EXISTS idx_classifications_created_at ON classifications(created_at);
CREATE INDEX IF NOT EXISTS idx_classifications_industry ON classifications(industry);

-- Table for API metrics
CREATE TABLE IF NOT EXISTS api_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    endpoint VARCHAR(100) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER NOT NULL,
    response_time DECIMAL(8,3) NOT NULL,
    instance_id VARCHAR(50),
    user_ip INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for metrics analysis
CREATE INDEX IF NOT EXISTS idx_api_metrics_endpoint ON api_metrics(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_metrics_created_at ON api_metrics(created_at);
CREATE INDEX IF NOT EXISTS idx_api_metrics_status ON api_metrics(status_code);

-- Table for system health tracking
CREATE TABLE IF NOT EXISTS health_checks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instance_id VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    redis_healthy BOOLEAN,
    celery_healthy BOOLEAN,
    openai_healthy BOOLEAN,
    response_time DECIMAL(8,3),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    details JSONB
);

-- Index for health monitoring
CREATE INDEX IF NOT EXISTS idx_health_checks_instance ON health_checks(instance_id);
CREATE INDEX IF NOT EXISTS idx_health_checks_created_at ON health_checks(created_at);

-- Table for cache statistics
CREATE TABLE IF NOT EXISTS cache_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    total_keys INTEGER NOT NULL,
    memory_used VARCHAR(20),
    hit_rate DECIMAL(5,2),
    instance_id VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create a view for recent classification analytics
CREATE OR REPLACE VIEW recent_classifications AS
SELECT 
    industry,
    classification,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence,
    AVG(processing_time) as avg_processing_time,
    COUNT(*) FILTER (WHERE cached = true) as cached_count,
    DATE_TRUNC('hour', created_at) as hour
FROM classifications 
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY industry, classification, DATE_TRUNC('hour', created_at)
ORDER BY hour DESC, count DESC;

-- Create a view for API performance metrics
CREATE OR REPLACE VIEW api_performance AS
SELECT 
    endpoint,
    method,
    COUNT(*) as total_requests,
    AVG(response_time) as avg_response_time,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time) as p95_response_time,
    COUNT(*) FILTER (WHERE status_code >= 200 AND status_code < 300) as success_count,
    COUNT(*) FILTER (WHERE status_code >= 400) as error_count,
    DATE_TRUNC('hour', created_at) as hour
FROM api_metrics 
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY endpoint, method, DATE_TRUNC('hour', created_at)
ORDER BY hour DESC, total_requests DESC;

-- Create a function to clean up old data
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
BEGIN
    -- Delete classifications older than 30 days
    DELETE FROM classifications WHERE created_at < NOW() - INTERVAL '30 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Delete API metrics older than 7 days
    DELETE FROM api_metrics WHERE created_at < NOW() - INTERVAL '7 days';
    
    -- Delete health checks older than 3 days
    DELETE FROM health_checks WHERE created_at < NOW() - INTERVAL '3 days';
    
    -- Delete cache stats older than 1 day
    DELETE FROM cache_stats WHERE created_at < NOW() - INTERVAL '1 day';
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions to the classifier user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO classifier;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO classifier;
GRANT EXECUTE ON FUNCTION cleanup_old_data() TO classifier;

-- Insert initial health check
INSERT INTO health_checks (instance_id, status, redis_healthy, celery_healthy, openai_healthy, response_time)
VALUES ('init', 'healthy', true, true, true, 0.001);

COMMIT;
