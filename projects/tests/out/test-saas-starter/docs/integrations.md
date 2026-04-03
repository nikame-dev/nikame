
### Cache-Aside Integration
**Status:** Active 🟢
**Components:** Postgres + Dragonfly
**Tuning:** TTL set to 3600s (optimized for balanced)

The Matrix Engine has automatically injected a cache-aside layer. Wrap any expensive database repository calls with `@cache_query(prefix="users")`.
*Because multi-tenancy is active, all cache keys will be automatically prefixed with the current active tenant ID to prevent cross-tenant data leakage.*


### Token Revocation List (Blacklist)
**Status:** Active 🟢
**Components:** Auth + Dragonfly

Because you selected Auth alongside a Cache, stateless JWTs can now be instantly revoked. 
When a user logs out, their token signature is inserted into Dragonfly. The authentication middleware will automatically check this fast-cache before trusting any valid JWT signatures.



### Distributed Tracing (OpenTelemetry)
**Status:** Active 🟢
**Components:** OpenTelemetry Collector / Tempo

A context propagator has been wired directly into the FastApi `lifespan`. This intercepts incoming HTTP requests, intercepts downstream database queries, and intercepts outgoing event messages. This guarantees full end-to-end trace visibility in Tempo/Grafana without manual span tracking in every router.


### multi_tenancy
Org-based data isolation (Multi-tenancy)


### stripe
Stripe subscription billing and webhook integration
