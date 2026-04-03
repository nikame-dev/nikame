
### Auth Event Bus
**Status:** Active 🟢
**Components:** Auth + RedPanda

Because your stack contains both an Authentication Provider and an Event Bus, Keycloak/Authentik lifecycle events (Sign Up, Login, Delete, Password Reset) are automatically caught and broadcast to the `auth.lifecycle.events` RedPanda topic. 

Any other microservice or worker can subscribe to this topic to react to user milestones (e.g. creating default records for new users or deleting PII upon account closure).



### Transactional Outbox Pattern
**Status:** Active 🟢
**Components:** Postgres + RedPanda

When building distributed systems, updating a database and publishing an event (dual-write) can lead to inconsistencies if the system crashes midway. The Matrix Engine has added the Transactional Outbox Pattern to fix this:

1. In your `async_session`, save business models AND `OutboxEvent` models in the exact same transaction.
2. A background process sweeps the Outbox table for unpublished events and guarantees delivery to RedPanda 'at-least-once'.



### Distributed Tracing (OpenTelemetry)
**Status:** Active 🟢
**Components:** OpenTelemetry Collector / Tempo

A context propagator has been wired directly into the FastApi `lifespan`. This intercepts incoming HTTP requests, intercepts downstream database queries, and intercepts outgoing event messages. This guarantees full end-to-end trace visibility in Tempo/Grafana without manual span tracking in every router.


### multi_tenancy
Org-based data isolation (Multi-tenancy)


### cron_jobs
Celery-backed background jobs and cron scheduler


### stripe
Stripe subscription billing and webhook integration
