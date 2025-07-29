-- =================================================================
-- GNB Dog Image Generation Backend - Database DDL Script
-- =================================================================
-- PostgreSQL DDL script to create all necessary tables
-- Run this script to set up the database manually

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =================================================================
-- Create Database (run separately as superuser if needed)
-- =================================================================
-- CREATE DATABASE gnb_dog_images;

-- =================================================================
-- IMAGE GENERATIONS TABLE
-- =================================================================
-- Table to track all image generation requests
CREATE TABLE image_generations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Original image information
    original_image_filename VARCHAR(255),
    original_image_url TEXT,
    original_image_size INTEGER,
    original_image_format VARCHAR(50),
    
    -- Generated image information
    generated_image_url TEXT,
    generated_image_size INTEGER,
    
    -- Processing information
    prompt_used TEXT,
    dog_description TEXT,
    processing_time REAL,
    status VARCHAR(50) DEFAULT 'pending',
    
    -- Azure AI information
    azure_response_data JSONB,
    error_message TEXT,
    
    -- Logo overlay information
    logo_applied BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for better query performance
CREATE INDEX idx_image_generations_status ON image_generations(status);
CREATE INDEX idx_image_generations_created_at ON image_generations(created_at DESC);
CREATE INDEX idx_image_generations_processing_time ON image_generations(processing_time);
CREATE INDEX idx_image_generations_logo_applied ON image_generations(logo_applied);

-- =================================================================
-- GENERATION STATISTICS TABLE
-- =================================================================
-- Table to store daily/periodic statistics and analytics
CREATE TABLE generation_statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Daily statistics
    total_generations INTEGER DEFAULT 0,
    successful_generations INTEGER DEFAULT 0,
    failed_generations INTEGER DEFAULT 0,
    
    -- Performance metrics
    average_processing_time REAL DEFAULT 0.0,
    total_processing_time REAL DEFAULT 0.0,
    
    -- Resource usage
    total_images_processed INTEGER DEFAULT 0,
    total_storage_used BIGINT DEFAULT 0, -- in bytes
    
    -- Error tracking
    azure_api_errors INTEGER DEFAULT 0,
    image_processing_errors INTEGER DEFAULT 0,
    logo_overlay_errors INTEGER DEFAULT 0
);

-- Create indexes for statistics queries
CREATE INDEX idx_generation_statistics_date ON generation_statistics(date DESC);
CREATE INDEX idx_generation_statistics_success_rate ON generation_statistics(successful_generations, total_generations);

-- =================================================================
-- USEFUL VIEWS FOR ANALYTICS
-- =================================================================

-- View for daily statistics summary
CREATE VIEW daily_generation_summary AS
SELECT 
    DATE(created_at) as generation_date,
    COUNT(*) as total_requests,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_requests,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_requests,
    ROUND(
        (COUNT(CASE WHEN status = 'completed' THEN 1 END)::DECIMAL / COUNT(*) * 100), 2
    ) as success_rate_percent,
    AVG(processing_time) as avg_processing_time,
    SUM(processing_time) as total_processing_time,
    COUNT(CASE WHEN logo_applied = true THEN 1 END) as logo_applied_count
FROM image_generations 
WHERE created_at IS NOT NULL
GROUP BY DATE(created_at)
ORDER BY generation_date DESC;

-- View for recent generation activity
CREATE VIEW recent_generations AS
SELECT 
    id,
    original_image_filename,
    status,
    processing_time,
    logo_applied,
    created_at,
    completed_at,
    CASE 
        WHEN status = 'completed' AND completed_at IS NOT NULL 
        THEN EXTRACT(EPOCH FROM (completed_at - created_at))
        ELSE NULL 
    END as total_duration_seconds
FROM image_generations 
ORDER BY created_at DESC 
LIMIT 100;

-- =================================================================
-- FUNCTIONS FOR DATA MAINTENANCE
-- =================================================================

-- Function to cleanup old generation records (optional)
CREATE OR REPLACE FUNCTION cleanup_old_generations(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM image_generations 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * days_to_keep;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to update daily statistics
CREATE OR REPLACE FUNCTION update_daily_statistics(target_date DATE DEFAULT CURRENT_DATE)
RETURNS VOID AS $$
DECLARE
    stats_record RECORD;
BEGIN
    -- Calculate statistics for the target date
    SELECT 
        COUNT(*) as total_gens,
        COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_gens,
        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_gens,
        COALESCE(AVG(processing_time), 0) as avg_time,
        COALESCE(SUM(processing_time), 0) as total_time,
        COUNT(*) as total_images,
        COALESCE(SUM(generated_image_size), 0) as total_storage,
        COUNT(CASE WHEN error_message LIKE '%Azure%' THEN 1 END) as azure_errors,
        COUNT(CASE WHEN error_message LIKE '%ImageProcessing%' THEN 1 END) as image_errors,
        COUNT(CASE WHEN error_message LIKE '%LogoOverlay%' THEN 1 END) as logo_errors
    INTO stats_record
    FROM image_generations 
    WHERE DATE(created_at) = target_date;
    
    -- Insert or update statistics record
    INSERT INTO generation_statistics (
        date, total_generations, successful_generations, failed_generations,
        average_processing_time, total_processing_time, total_images_processed,
        total_storage_used, azure_api_errors, image_processing_errors, logo_overlay_errors
    ) VALUES (
        target_date, stats_record.total_gens, stats_record.successful_gens, stats_record.failed_gens,
        stats_record.avg_time, stats_record.total_time, stats_record.total_images,
        stats_record.total_storage, stats_record.azure_errors, stats_record.image_errors, stats_record.logo_errors
    )
    ON CONFLICT (date) DO UPDATE SET
        total_generations = EXCLUDED.total_generations,
        successful_generations = EXCLUDED.successful_generations,
        failed_generations = EXCLUDED.failed_generations,
        average_processing_time = EXCLUDED.average_processing_time,
        total_processing_time = EXCLUDED.total_processing_time,
        total_images_processed = EXCLUDED.total_images_processed,
        total_storage_used = EXCLUDED.total_storage_used,
        azure_api_errors = EXCLUDED.azure_api_errors,
        image_processing_errors = EXCLUDED.image_processing_errors,
        logo_overlay_errors = EXCLUDED.logo_overlay_errors;
END;
$$ LANGUAGE plpgsql;

-- =================================================================
-- SAMPLE QUERIES FOR TESTING
-- =================================================================

-- Test the tables are created correctly
-- SELECT COUNT(*) FROM image_generations;
-- SELECT COUNT(*) FROM generation_statistics;

-- Test the views
-- SELECT * FROM daily_generation_summary LIMIT 5;
-- SELECT * FROM recent_generations LIMIT 5;

-- =================================================================
-- GRANTS (adjust as needed for your environment)
-- =================================================================
-- Grant permissions to your application user
-- GRANT SELECT, INSERT, UPDATE, DELETE ON image_generations TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON generation_statistics TO your_app_user;
-- GRANT SELECT ON daily_generation_summary TO your_app_user;
-- GRANT SELECT ON recent_generations TO your_app_user;

-- =================================================================
-- COMPLETION MESSAGE
-- =================================================================
-- Database tables created successfully!
-- Next steps:
-- 1. Update your .env file with the database connection string
-- 2. Test the connection with your FastAPI application
-- 3. Start generating images! 