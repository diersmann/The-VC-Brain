# Operations runbook

This runbook describes the current Docker-first recovery workflow. It is safe for local development and disposable staging. Production RPO/RTO values, backup retention, alert ownership, and cloud-provider commands are not approved yet; do not treat the placeholders below as production commitments.

## Service ownership and first response

| Area | Primary owner | First checks |
|---|---|---|
| API / frontend | Application owner | `make ps`, `docker compose logs --tail=200 api frontend` |
| Worker / queue | Pipeline owner | `docker compose logs --tail=200 worker`, `/api/v1/ready` |
| PostgreSQL | Data owner | `make shell-db`, migration status, disk/connection health |
| MinIO snapshots | Data owner | bucket availability, object count, storage capacity |
| Security / privacy | Security owner | access logs, incident timeline, credential rotation |

If an owner is unavailable, record the escalation in the incident log and keep the system in its last known safe state. Never delete evidence or rewrite decision history during first response.

## Routine health and evidence preservation

```bash
make ps
curl -fsS http://localhost:8000/api/v1/health
curl -fsS http://localhost:8000/api/v1/ready
docker compose logs --tail=200 api worker
```

`/health` is a liveness check. `/ready` checks PostgreSQL, Redis, MinIO, and the worker heartbeat. Before investigating data symptoms, capture service logs and the current migration revision:

```bash
docker compose exec postgres psql -U "${POSTGRES_USER:-vc_brain}" -d "${POSTGRES_DB:-vc_brain}" -c 'select version_num from alembic_version;'
```

Logs and snapshots may contain sensitive information. Store incident artifacts in an access-controlled location and do not paste founder email, uploaded documents, or raw source content into tickets or chat.

## PostgreSQL backup and restore

The repository does not yet provision a production backup scheduler. Until one is approved, an operator may create a logical backup from a disposable or authorized environment:

```bash
mkdir -p ./tmp/backups
docker compose exec -T postgres pg_dump \
  -U "${POSTGRES_USER:-vc_brain}" \
  -d "${POSTGRES_DB:-vc_brain}" \
  --format=custom --no-owner --file=/tmp/vcbrain.dump
docker compose cp postgres:/tmp/vcbrain.dump ./tmp/backups/vcbrain-$(date -u +%Y%m%dT%H%M%SZ).dump
```

Restore only into a disposable database or an explicitly approved maintenance window. Verify the target identity before destructive restore operations; never restore over a shared developer volume with `make clean` as part of incident response.

```bash
docker compose cp ./tmp/backups/<validated-backup>.dump postgres:/tmp/restore.dump
docker compose exec -T postgres pg_restore \
  -U "${POSTGRES_USER:-vc_brain}" \
  -d "${POSTGRES_DB:-vc_brain}" \
  --no-owner --exit-on-error /tmp/restore.dump
docker compose run --rm migrate
make check
```

The backup drill is not complete until row counts, migration revision, source-snapshot object references, API readiness, and representative candidate/detail/memo reads are compared with the pre-drill manifest.

## MinIO snapshot recovery

PostgreSQL references immutable snapshots stored in MinIO. A database-only restore is incomplete if the referenced objects are absent. The local S3-compatible endpoint can be inspected with the MinIO client when it is installed:

```bash
mc alias set vcbrain http://localhost:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
mc ls --recursive vcbrain/${APP_MINIO_BUCKET:-vc-brain-snapshots}
```

Production backup, retention, encryption, cross-region replication, and restore credentials remain deployment-specific work. Do not invent a cloud bucket or retention policy in an incident.

## Migrations, rollback, and worker compatibility

Migrations run in the one-shot `migrate` service before API and worker startup:

```bash
make migrate
docker compose exec api /opt/venv/bin/alembic current
```

The default policy is forward-fix: stop incompatible workers, deploy compatible application code, apply the forward migration, then restart API and worker. A migration that may destroy or reinterpret data requires an explicit backup, a tested downgrade or compensating migration, and recorded approval. Do not use `alembic downgrade` against shared or production data without that approval.

Workers must remain compatible with the database schema during rolling restarts. Add nullable columns and dual-read/dual-write behavior first when a change crosses application versions; remove compatibility code only after all old workers are retired and the migration has been observed healthy.

## Incident checklist

1. Record start time, reporter, affected service, and current lifecycle/data symptoms.
2. Check `/health`, `/ready`, `make ps`, migration revision, and recent logs.
3. Preserve logs, job IDs, source IDs, opportunity IDs, and backup manifests without copying PII into the incident channel.
4. Stop automated collection or outreach if it could amplify the incident; preserve queued work for replay.
5. Choose the least destructive mitigation and record the exact command and operator.
6. Validate representative reads, queue behavior, snapshot availability, and audit events.
7. Record customer impact, root cause, corrective action, and follow-up owner.

## Recovery drill acceptance criteria

The following are required before VCB-094 can be marked complete:

- approved production RPO/RTO, retention, encryption, and access policy;
- scheduled PostgreSQL and MinIO backups with failure alerts;
- a disposable restore drill that verifies data, object references, migrations, readiness, and representative UI/API flows;
- a tested forward-fix and rollback/compensating-migration procedure;
- a rolling worker compatibility test;
- named incident owners and a dated review of the runbook.
