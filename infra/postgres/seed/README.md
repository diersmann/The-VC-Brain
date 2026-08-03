# Database seed policy

The repository does not commit a database snapshot. The former snapshot contained
public-profile demo rows and was removed to avoid distributing unnecessary personal
data and unreviewed source material.

For a local walkthrough, use the synthetic, deterministic, idempotent fixture:

```bash
make seed-demo
```

The optional `backend/scripts/import_public_inbound.py` importer is not part of
normal setup. It fetches official public pages, stores them as `public_demo`
references, and marks their source metadata as excluded from operational metrics.
Run it only after source-owner/legal review confirms the permitted collection,
retention, display, and model-use terms for each source.
