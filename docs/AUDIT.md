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

Local implementation checks: 71 catalog tests passed; 9 publisher tests passed; publisher production build and lint passed. Production and integration Compose files parse successfully. Tests use an actual RDF dataset/query engine behind the HTTP transport for semantic query and snapshot checks; they do not substitute for a real Fuseki persistence test.

Added coverage includes semantic cross-participant discovery, dataset detail, snapshot replacement, model-graph preservation, SHACL rejection preserving prior state, unregistered rejection, SELECT/ASK JSON bindings and limits, rejected update/remote operations, DPoP missing/mismatched binding fields, replay, malformed tokens and public-URL binding.

Compatible npm updates reduced the baseline advisory report from 12 to 6. Remaining: 4 high entries in the legacy Inrupt/serialize-javascript dependency chain, and 2 moderate Vitest/mocker entries. The package manager suggests major upgrades (Inrupt browser auth 5 and Vitest 4). These were not force-installed because the task requires preserving and verifying the real authentication path. The existing auth API builds and tests, but this is not a security signoff; assess/upgrade and verify against the real provider before public use.

The local Docker engine could not be started because computer-use permission was unavailable. Actual container build/startup, Fuseki timeout/PUT behavior and restart persistence are therefore pending the isolated GitHub Actions integration job or a run on the server. Remote DNS/TLS and TMDT acceptance remain pending. P10 semantic-model ingestion is intentionally deferred.
