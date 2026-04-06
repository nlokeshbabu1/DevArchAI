-- Add detected_stack column to scans table
ALTER TABLE scans ADD COLUMN IF NOT EXISTS detected_stack JSON;

-- Comment to describe the column
COMMENT ON COLUMN scans.detected_stack IS 'Detected technology stack from repository analysis';

-- Verify column was added
\d scans
