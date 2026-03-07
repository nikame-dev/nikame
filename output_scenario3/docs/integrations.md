
### Auth Event Bus
**Status:** Active 🟢
**Components:** Auth + RedPanda

Because your stack contains both an Authentication Provider and an Event Bus, Keycloak/Authentik lifecycle events (Sign Up, Login, Delete, Password Reset) are automatically caught and broadcast to the `auth.lifecycle.events` RedPanda topic. 

Any other microservice or worker can subscribe to this topic to react to user milestones (e.g. creating default records for new users or deleting PII upon account closure).



### Cache-Aside Integration
**Status:** Active 🟢
**Components:** Postgres + Dragonfly
**Tuning:** TTL set to 3600s (optimized for balanced)

The Matrix Engine has automatically injected a cache-aside layer. Wrap any expensive database repository calls with `@cache_query(prefix="users")`.
*Because multi-tenancy is active, all cache keys will be automatically prefixed with the current active tenant ID to prevent cross-tenant data leakage.*


### Event Idempotency Integration
**Status:** Active 🟢
**Components:** RedPanda + Dragonfly
**Tuning:** ID Tracking TTL set to 7200s

The Matrix Engine has automatically injected an Exactly-Once processing layer. Wrap any Kafka consumer functions with `@idempotent_consumer`. The system will automatically check Dragonfly for the Message ID before processing and drop duplicates.



### Transactional Outbox Pattern
**Status:** Active 🟢
**Components:** Postgres + RedPanda

When building distributed systems, updating a database and publishing an event (dual-write) can lead to inconsistencies if the system crashes midway. The Matrix Engine has added the Transactional Outbox Pattern to fix this:

1. In your `async_session`, save business models AND `OutboxEvent` models in the exact same transaction.
2. A background process sweeps the Outbox table for unpublished events and guarantees delivery to RedPanda 'at-least-once'.



### Event-Driven Search Sync
**Status:** Active 🟢
**Components:** Postgres -> RedPanda -> Elasticsearch

The Matrix Engine detected your CQRS architecture. Instead of dual-writing to the database and search engine synchronously (which causes latency and reliability issues), changes are streamed through RedPanda:

1. Insert data to Postgres.
2. Publish `entity.created` event to RedPanda via `publish_search_sync_event(entity)`.
3. An asynchronous consumer picks up the event and indexes it into Elasticsearch.



### Token Revocation List (Blacklist)
**Status:** Active 🟢
**Components:** Auth + Dragonfly

Because you selected Auth alongside a Cache, stateless JWTs can now be instantly revoked. 
When a user logs out, their token signature is inserted into Dragonfly. The authentication middleware will automatically check this fast-cache before trusting any valid JWT signatures.



### Distributed Tracing (OpenTelemetry)
**Status:** Active 🟢
**Components:** OpenTelemetry Collector / Tempo

A context propagator has been wired directly into the FastApi `lifespan`. This intercepts incoming HTTP requests, intercepts downstream database queries, and intercepts outgoing event messages. This guarantees full end-to-end trace visibility in Tempo/Grafana without manual span tracking in every router.
