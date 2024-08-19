CREATE OR REPLACE FUNCTION backup_on_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' OR TG_OP = 'UPDATE' THEN
        INSERT INTO users_backup (email, password, created_at, role)
        VALUES (OLD.email, OLD.password, OLD.created_at, OLD.role)
        ON CONFLICT (email)
        DO NOTHING;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO users_backup (email, password, created_at, role)
        VALUES (NEW.email, NEW.password, NEW.created_at, NEW.role)
        ON CONFLICT (email)
        DO NOTHING;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_backup_trigger
AFTER INSERT OR UPDATE OR DELETE
ON users
FOR EACH ROW
EXECUTE FUNCTION backup_on_change();
