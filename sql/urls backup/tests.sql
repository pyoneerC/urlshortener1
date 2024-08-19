SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_name = 'urls_backup'
) AS table_exists;

SELECT * from urls_backup;