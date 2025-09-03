# ADR-0011 — Supervisor-only Operations
**Context.** On some hosts, docker CLI is unavailable or the add-on container isn’t visible by name. Diagnostics must not rely on `docker exec/ps`.  
**Decision.** All operational visibility is emitted to Supervisor logs (`ha addons logs`). run.sh prints DIAG + 15s health summaries to stdout; Python emits heartbeats; optional file-to-stdout forwarder mirrors key Python lines.  
**Consequences.** All runbooks use `ha` CLI; routine ops avoid container-internal flags. Respawn drills and health checks are verified solely from Supervisor logs.
