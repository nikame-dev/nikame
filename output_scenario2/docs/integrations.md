
### Cache-Aside Integration
**Status:** Active 🟢
**Components:** Postgres + Dragonfly
**Tuning:** TTL set to 3600s (optimized for balanced)

The Matrix Engine has automatically injected a cache-aside layer. Wrap any expensive database repository calls with `@cache_query(prefix="users")`.



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
