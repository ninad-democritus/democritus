-- MySQL initialization script for OpenMetadata
-- Create additional users if needed and set proper permissions

-- The database and user are already created through environment variables
-- This script can be used for additional setup if needed

-- Grant all privileges to openmetadata_user on the database
GRANT ALL PRIVILEGES ON openmetadata_db.* TO 'openmetadata_user'@'%';
FLUSH PRIVILEGES;

-- Set MySQL settings that OpenMetadata might need (MySQL 8.0 compatible)
SET GLOBAL sql_mode = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';
