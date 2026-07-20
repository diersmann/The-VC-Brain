# FirstCheck24 database seed

`firstcheck24_seed.sql.gz` is a portable, data-only PostgreSQL snapshot for the hackathon demo. It is intended to be restored after Alembic has created the schema.

Snapshot contents (2026-07-20):

- 112 founder/person records
- 34 opportunities and 34 founder links
- 742 source snapshots
- 1,458 observations
- 105 claims and 105 assessments
- 4,195 score snapshots
- 2 investment theses

The snapshot contains public-source demo/research data. Credentials, API keys, database passwords, Docker volumes, and Alembic's internal version row are not included.

The seed is generated against the current Alembic head and includes explicit values for all required thesis discovery fields, including `discovery_queries` and `source_freshness_days`.

## Restore

Start the stack and apply migrations:

```bash
docker compose up -d
docker compose exec api /opt/venv/bin/alembic upgrade head
```

Restore into an empty, migrated `vc_brain` database:

```bash
gunzip -c infra/postgres/seed/firstcheck24_seed.sql.gz \
  | docker compose exec -T postgres sh -lc \
    'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Do not import the seed repeatedly into the same database because primary-key and unique constraints will reject duplicate rows.

## Recreate the snapshot

```bash
docker compose exec -T postgres sh -lc \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    --data-only --exclude-table=alembic_version \
    --no-owner --no-privileges --format=plain' \
  | gzip -9 > infra/postgres/seed/firstcheck24_seed.sql.gz
```
