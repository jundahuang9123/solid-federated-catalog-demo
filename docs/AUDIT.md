# Baseline audit — 2026-09-15

Upstream catalog: `632e735a50a2a709cd31a10be33aae5a0ab12bd2`.
Upstream publisher: `6485e30c8daaafcdc4b1de2a6e3f712f48dc025e`.
ConstructDCAT vocabulary: `2effb755897b99342f8405afac96425f6c13649c`.

Before changes: catalog 36 tests passed; publisher 9 tests passed and production build passed. Local Python 3.11.2; Node 25.9.0 (outside Inrupt's supported range; deployment/CI use Node 22). Existing publisher installation reports 12 advisories (3 moderate, 9 high); audit and remediation tracked below.

## Blockers found before architecture changes

- Compose exposes Fuseki, uses development credentials, has no named persistent volume, and requires a mode profile.
- Graph replacement uses DELETE followed by POST; failed writes can destroy the previous snapshot. Replace via Graph Store PUT.
- Registry refresh failure reuses stale members indefinitely. Publication must fail closed after expiry; production TTL defaults to zero.
- Authentication accepts token-supplied issuers, does not require cnf.jkt, and does not verify ath or replay. Pin the TMDT issuer and harden DPoP before a public run.
- User SPARQL endpoint and UI are absent.
- Docker daemon was unavailable at initial audit. Startup, restart persistence and real Fuseki queries remain unverified until the integration suite runs.
- Real browser-to-TMDT authentication, Pod reads, registry accessibility, DNS and HTTPS require infrastructure details. Unit tests do not establish live interoperability.

Existing architecture retained: FastAPI mode registration, registry contract, SHACL pipeline, graph naming, discovery and publisher authenticated session.fetch. EDC remains a non-operational stub. No Solid server is added to production.

## Implemented verification

Local implementation checks: 75 catalog tests passed; 9 publisher tests passed; publisher production build and lint passed. Production and integration Compose files parse successfully. Tests use an actual RDF dataset/query engine behind the HTTP transport for semantic query and snapshot checks; they do not substitute for a real Fuseki persistence test.

Added coverage includes semantic cross-participant discovery, dataset detail, snapshot replacement, model-graph preservation, SHACL rejection preserving prior state, unregistered rejection, SELECT/ASK JSON bindings and limits, rejected update/remote operations, DPoP missing/mismatched binding fields, replay, malformed tokens and public-URL binding.

The publisher dependency audit initially reported 12 advisories. After reviewing the [Inrupt migration notes](https://github.com/inrupt/solid-client-authn-js/releases), the demo uses Inrupt browser authentication 5.0.0 and Vitest 4.1.11. Inrupt 4 replaces the unmaintained OIDC dependency while preserving this application's public session API; Inrupt 5 requires Node 22/24. The final install reports zero npm advisories. The existing login/session.fetch flow remains, with real TMDT verification still required.

The local Docker engine could not be started because computer-use permission was unavailable. The [GitHub Actions integration run](https://github.com/jundahuang9123/solid-federated-catalog-demo/actions/runs/34944904684) instead passed on Linux: real Fuseki 5.1.0 startup, publication, discovery, query, membership failure, replacement/isolation and persistence through complete container recreation. The first run exposed a readiness-probe connection-reset race; retry handling was fixed and the rerun passed. The browser SPARQL page was also exercised with offline fixtures and returned the two expected semantic matches.

Python dependencies are constrained to the tested environment (`catalog/constraints.txt`); publisher dependencies are locked. Production proxy build/configuration checks are included in CI. Remote DNS/TLS and real TMDT acceptance remain pending. P10 semantic-model ingestion is intentionally deferred.
