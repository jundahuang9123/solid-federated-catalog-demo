# Architecture

```text
External TMDT:
  Solid-OIDC provider + participant WebIDs
  Participant A Pod / catalog/cat.ttl
  Participant B Pod / catalog/cat.ttl
  Registry container -> participant records -> foaf:member WebIDs

Browser publisher (static files served through Caddy)
  -> Solid login/session.fetch -> reads participant's Pod
  -> previews RDF -> POST https://catalog-host/catalog

Supervisor VM:
  Caddy HTTPS -> FastAPI catalog -> internal Fuseki/TDB2 named graphs
            -> built publisher UI on a second hostname
```

The participant Pod is authoritative for original resources. The publisher is a browser client, not a storage service. The registry controls membership. The catalog validates submitted metadata and materializes a searchable index. Fuseki stores that index persistently. EDC is a separate non-operational stub retained from upstream.

## Publication semantics

Authentication identifies a WebID through the configured trusted TMDT issuer and verifies the DPoP proof. Membership is checked before SHACL validation. Successful publication replaces exactly `urn:catalog:<percent-encoded-WebID>` using Graph Store PUT. No graph name is taken from user-supplied metadata. Invalid RDF/SHACL or rejected membership does not reach storage. A failed PUT is not preceded by a destructive DELETE. Concurrent successful publications for one participant use last-committed-write semantics; no version conflict protocol is implemented.

The default registry contract follows an LDP container's `ldp:contains` resources and extracts `foaf:member` WebIDs. Unreadable or syntactically malformed resources fail closed. A record without configured membership predicates grants no membership. Production uses zero membership cache TTL; configured positive TTLs provide a bounded revocation delay, and expired stale entries are never used for publication.

## Querying

`POST /sparql` executes SELECT/ASK against one materialized Fuseki dataset. No remote query requests through SERVICE, FROM or extension functions are allowed. Discovery keeps its original simplified query helper; the public query API preserves RDF JSON terms. This is cross-named-graph querying inside one dataset, **not distributed SPARQL federation**.

## Semantic models (deferred)

Reserve separate graphs such as `urn:model:<participant>:<model-id>` and `urn:system:provenance`. Catalog publication never deletes them. No semantic-model ingestion or synchronization endpoint is implemented in this milestone. A later design must explicitly map catalog model-resource links to index graph names and confirm which Construct-DCAT property conveys that link; it must not rely on accidental URI equality. Do not imply `cx:usesOntology` automatically names a locally indexed graph.

## Limits and pending validation

Only public demo metadata belongs in this index: discovery/query endpoints expose indexed metadata without read authorization. Do not upload confidential Pod content simply because a participant can read it. The deployment does not provision identities, change Pod permissions or create registry membership automatically.

Authentication is deliberately scoped to a configured, trusted TMDT issuer. DPoP cnf.jkt, ath, public asymmetric key, typ, method, URI, timestamp and replay checks have synthetic tests; those are not evidence of a real Solid session. Replay protection is bounded and process-local; no multi-worker or durable replay store is claimed. Nonce challenge support and distributed identity/provider discovery are not implemented.
