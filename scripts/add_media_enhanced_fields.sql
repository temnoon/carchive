-- Add new columns to media table
ALTER TABLE media ADD COLUMN IF NOT EXISTS original_file_id VARCHAR;
ALTER TABLE media ADD COLUMN IF NOT EXISTS file_name VARCHAR;
ALTER TABLE media ADD COLUMN IF NOT EXISTS source_url VARCHAR;
ALTER TABLE media ADD COLUMN IF NOT EXISTS is_generated BOOLEAN DEFAULT FALSE;

-- Create index on original_file_id for faster lookup
CREATE INDEX IF NOT EXISTS ix_media_original_file_id ON media (original_file_id);

-- Update the is_generated flag for files in the dalle-generations folder
UPDATE media
SET is_generated = TRUE
WHERE file_path LIKE '%dalle-generations%';