# Backend database migrations

Run Alembic commands from the `backend/` directory. Set `DATABASE_URL` to the
PostgreSQL connection string for the target environment; if it is not set,
Alembic uses `postgresql+asyncpg://postgres:postgrespassword@db:5432/student_events_db`.

Create and apply the initial migration:

```sh
alembic revision --autogenerate -m "Initial RBAC and Auth migration"
alembic upgrade head
```

Autogeneration connects to the configured database and compares its schema
against the SQLAlchemy models. Review the generated revision before applying
it, especially when working with PostgreSQL enums.

The admin API stores an optional organization contact email. Include model
changes in a new Alembic revision and apply it with `alembic upgrade head`
before deploying the updated API to an existing database.
