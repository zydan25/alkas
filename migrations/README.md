# Database migrations

The repository intentionally keeps database evolution under Flask-Migrate/Alembic.

For the first deployment:

1. Create the PostgreSQL database.
2. Enable the PostgreSQL extension required by the resource/time exclusion constraint:

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;
```

3. Initialize and create the first migration:

```bash
flask --app wsgi db init
flask --app wsgi db migrate -m "initial schema"
flask --app wsgi db upgrade
```

After that, schema changes are applied only through:

```bash
flask --app wsgi db migrate -m "describe change"
flask --app wsgi db upgrade
```

Never edit production tables as the normal development workflow.
