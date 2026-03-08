
### Cache-Aside Integration
**Status:** Active 🟢
**Components:** Postgres + Dragonfly
**Tuning:** TTL set to 3600s (optimized for balanced)

The Matrix Engine has automatically injected a cache-aside layer. Wrap any expensive database repository calls with `@cache_query(prefix="users")`.



### Token Revocation List (Blacklist)
**Status:** Active 🟢
**Components:** Auth + Dragonfly

Because you selected Auth alongside a Cache, stateless JWTs can now be instantly revoked. 
When a user logs out, their token signature is inserted into Dragonfly. The authentication middleware will automatically check this fast-cache before trusting any valid JWT signatures.


### multi_tenancy
Org-based data isolation (Multi-tenancy)


### stripe
Stripe subscription billing and webhook integration
