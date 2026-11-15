# Backend database migrations

Migrations live in `alembic/versions/`. They are applied **automatically** when
the API starts and when `python -m app.seed` runs, so normally nothing needs to
be done by hand. A database created by an older version of the app (tables
built with `create_all`, no `alembic_version` table) is detected and adopted.

Run Alembic commands from the `backend/` directory. The database URL comes from
`DATABASE_URL` (or the repository's `.env`), the same as the application.

After changing a model, create a new revision and review it before committing:

```sh
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
alembic check        # verifies models and migrations are in sync
```

Autogenerate does not detect new values in PostgreSQL enums or data changes;
add those by hand (see `0002_event_lifecycle_and_tickets.py` for an example).
