SELECT version();

SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_name = 'users'
) AS table_exists;

SELECT * from users;