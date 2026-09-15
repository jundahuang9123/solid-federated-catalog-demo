# Federated Solid Catalog Live Demonstrator

## 1. Objective

Turn the existing Solid federated-catalog prototypes into a persistent, network-accessible demonstrator that can run on a supervisor-provided server and interact with existing TMDT Solid infrastructure.

Existing repositories:

- `jundahuang9123/Dual-Federated-Catalog-Solid-EDC-`
  - central push-based federated catalog
  - FastAPI
  - Apache Fuseki
  - registry membership checking
  - SHACL validation
  - named participant graphs
  - discovery API/UI
  - internal SPARQL querying already implemented

- `jundahuang9123/solid-federated-catalog-publisher`
  - participant-side publisher
  - Solid-OIDC login
  - loads catalog RDF from Solid Pod
  - previews RDF
  - pushes catalog metadata to federated catalog

The target system is:

```text
Existing TMDT Solid infrastructure
│
├── Participant Pod A
├── Participant Pod B
├── Participant Pod C
└── Solid registry
        │
        │
        ▼
Participant-side Publisher
        │
        │ HTTPS POST /catalog
        ▼
Supervisor-provided server
│
├── Federated Catalog API/UI
└── Apache Fuseki / persistent RDF index
        │
        ├── catalog discovery
        └── SPARQL query interface
```

The central server MUST NOT host or own the participant Solid Pods.

For Phase 1, use existing TMDT Solid infrastructure for participant Pods and registry resources.

---

# 2. Architectural Principles

Preserve these decisions unless implementation evidence requires a change.

### Central catalog is a materialized metadata index

Participants retain their original Solid resources.

The central service stores validated published metadata in Fuseki for discovery and querying.

The central catalog is therefore not the authoritative source of participant data.

### One named catalog graph per participant

Keep the current convention:

```text
urn:catalog:<encoded-WebID>
```

A new successful publication by a participant replaces that participant's current catalog graph.

This provides simple snapshot/update semantics for the demonstrator.

### Do not merge semantic models into the catalog graph

Future semantic models should use separate named graphs.

For example:

```text
urn:catalog:<participant>
urn:model:<participant>:<model-id>
urn:system:provenance
```

Publishing a new DCAT catalog must not delete indexed semantic-model graphs.

### Solid infrastructure is external

Do not add Community Solid Server to the production `docker-compose.yml`.

A separate local/demo/test Compose file may later contain CSS, but production deployment must communicate with existing external Solid infrastructure.

### Fuseki should not be publicly exposed in production

Only the catalog service should normally be internet-facing.

SPARQL access should be proxied/exposed through the application with appropriate restrictions.

---

# 3. Phase 0 — Audit and Stabilize Current Repositories

Before adding substantial functionality, inspect both repositories and verify the existing architecture.

Confirm:

- current Docker Compose starts FastAPI + Fuseki correctly;
- `/catalog` publication works in trusted-header development mode;
- registry membership check works;
- SHACL validation works;
- publication creates/replaces participant named graph;
- `/datasets` reads data from Fuseki;
- `/datasets/detail` works;
- current `FusekiClient.query()` correctly executes SPARQL;
- publisher can load local RDF;
- publisher can target a configurable remote catalog URL;
- existing automated tests pass.

Do not refactor working code merely for stylistic reasons.

Document any discovered blockers before changing architecture.

Acceptance criteria:

```text
docker compose ...
pytest / npm test ...
```

must establish a known-good baseline.

---

# 4. Phase 1 — Production-Oriented Central Server Deployment

Goal:

Make `Dual-Federated-Catalog-Solid-EDC-` deployable on a normal Linux VM using one simple Docker Compose command.

Desired operator workflow:

```bash
git clone <repo>
cp .env.example .env
# configure environment
docker compose up -d --build
```

## Required changes

### 4.1 Persistent Fuseki storage

Fuseki data must survive:

```bash
docker compose down
docker compose up -d
```

Add an explicit Docker volume/bind mount for Fuseki/TDB storage.

Verify persistence through an integration test:

1. publish participant metadata;
2. stop containers;
3. restart containers;
4. query `/datasets`;
5. previously published dataset still exists.

### 4.2 Production Compose profile

Separate local-development assumptions from server deployment where useful.

Suggested structure:

```text
docker-compose.yml
docker-compose.prod.yml
.env.example
```

or profiles if simpler.

Production deployment should include:

```text
catalog
fuseki
reverse-proxy
```

Reverse proxy can be Caddy, Traefik, or nginx.

Prefer the simplest maintainable solution.

### 4.3 HTTPS/domain configuration

The application should support deployment behind a hostname such as:

```text
https://federated-catalog.example.org
```

Requirements:

- HTTPS;
- forwarded headers handled correctly;
- configurable external/base URL;
- correct CORS;
- no hardcoded localhost URLs in production;
- publisher can target public catalog URL.

### 4.4 Network exposure

Production defaults:

```text
443      public
80       optional HTTP→HTTPS redirect
8000     internal only
3030     internal only
```

Do not expose Fuseki admin/query/update interfaces directly to the public internet.

### 4.5 Environment configuration

Create/update `.env.example`.

Include at least:

```text
CATALOG_MODE=solid

FUSEKI_URL=
FUSEKI_USER=
FUSEKI_PASSWORD=

SOLID_REGISTRY_URL=
SOLID_REGISTRY_CONTRACT_PATH=
SOLID_REGISTRY_CACHE_TTL_SECONDS=

SOLID_AUTH_MODE=
SOLID_AUTH_REQUIRE_DPOP=

CATALOG_PUBLIC_URL=
CATALOG_CORS_ORIGINS=
```

Generate no real secrets in Git.

### 4.6 Health/readiness

Retain:

```text
/health
/ready
/status
```

Make them meaningful for deployment.

`/ready` should report failure when critical dependencies are unavailable.

---

# 5. Phase 2 — Real TMDT Solid Integration

Goal:

Connect the deployed central catalog to actual TMDT Solid identities, Pods, and registry resources.

Do NOT create a new Solid server unless explicitly required.

## Required configuration

Use existing external TMDT infrastructure for:

```text
Participant WebIDs
Participant Pods
Solid registry
Solid-OIDC provider
```

Create at least two controlled demo participants, for example:

```text
Participant A
Participant B
```

A third unregistered identity is useful for demonstrating rejection.

Each participant should have a Solid catalog resource, preferably following the existing convention:

```text
<Pod root>/catalog/cat.ttl
```

The catalog should contain valid DCAT/Construct-DCAT demo data.

## Registry

Use the existing registry contract unless the deployed TMDT structure proves incompatible.

Expected model:

```text
registry LDP container
   ldp:contains participant resource

participant resource
   foaf:member <participant WebID>
```

Verify:

- registered participant → publish allowed;
- unregistered participant → HTTP 403;
- unreachable/malformed registry → fail closed.

---

# 6. Phase 3 — Strict Solid-OIDC End-to-End Authentication

Current trusted-header mode is useful for development but not sufficient for the live system.

Goal:

Confirm actual browser → catalog authentication using Solid-OIDC and DPoP.

Use the existing publisher request-capture tooling first.

Verify actual request contains the expected security material:

```text
Authorization
DPoP
access token cnf.jkt
DPoP htu
DPoP htm = POST
```

Then test against the real central catalog.

Expected production path:

```text
Solid login
   ↓
authenticated publisher session
   ↓
POST https://<catalog>/catalog
   ↓
catalog validates Solid identity
   ↓
WebID checked against registry
```

Do not claim strict Solid-OIDC authentication works until verified end-to-end.

Keep `trusted-header` available only as an explicitly marked local-development/demo fallback.

---

# 7. Phase 4 — User-Facing SPARQL Query Capability

The storage layer already executes SPARQL internally.

Do not rewrite this layer unnecessarily.

The task is to expose controlled querying to users.

## 7.1 Application query endpoint

Add something similar to:

```text
POST /sparql
```

Input:

```json
{
  "query": "SELECT ..."
}
```

For Phase 1 support:

```text
SELECT
ASK
```

Optional if straightforward:

```text
CONSTRUCT
DESCRIBE
```

Explicitly reject SPARQL Update operations:

```text
INSERT
DELETE
LOAD
CLEAR
CREATE
DROP
MOVE
COPY
ADD
etc.
```

Never expose arbitrary Fuseki update capabilities.

Implement:

- request-size limit;
- query timeout;
- sensible result-size limit;
- error responses;
- SPARQL syntax error handling.

For SELECT, preserve useful RDF binding information if practical:

```json
{
  "type": "uri",
  "value": "...",
  "datatype": "...",
  "xml:lang": "..."
}
```

rather than flattening everything permanently to plain strings.

Existing internal discovery code may continue using its simplified helper if that avoids unnecessary regression risk.

## 7.2 SPARQL UI

Add a new tab/page:

```text
Datasets
SPARQL
Status
```

SPARQL page should include:

- text editor / textarea;
- Run Query button;
- result table;
- execution/error message;
- example queries selector.

Provide several built-in example queries.

Example 1 — all datasets:

```sparql
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?graph ?dataset ?title
WHERE {
  GRAPH ?graph {
    ?dataset a dcat:Dataset .
    OPTIONAL { ?dataset dct:title ?title }
  }
}
ORDER BY ?title
```

Example 2 — participants:

```sparql
PREFIX dcat: <http://www.w3.org/ns/dcat#>

SELECT DISTINCT ?graph
WHERE {
  GRAPH ?graph {
    ?dataset a dcat:Dataset .
  }
}
```

Example 3 — Construct-DCAT semantic discovery.

Use actual final Construct-DCAT namespace/property names from the repository/project definition rather than inventing new ones.

---

# 8. Phase 5 — Construct-DCAT Demo Dataset

Create a small but semantically meaningful demonstration dataset.

Do not make the demo merely "Alice dataset / Bob dataset."

Use a construction-domain competency question.

Suggested question:

```text
Find datasets describing wall/building-element concepts across multiple participants.
```

Participant A could publish BIM/IFC-oriented metadata.

Participant B could publish AAS/semantic-model-oriented metadata.

The two datasets should not depend on matching free-text keywords alone.

Construct-DCAT semantic anchors should allow the SPARQL query to identify them consistently.

Keep demo data deterministic and version controlled.

Suggested location:

```text
demo-data/
    participant-a/
        catalog-v1.ttl
        catalog-v2.ttl
    participant-b/
        catalog-v1.ttl
    invalid/
        invalid-catalog.ttl
```

`catalog-v2.ttl` should visibly differ from `catalog-v1.ttl` so update propagation can be demonstrated.

---

# 9. Phase 6 — Live Update Demonstration

Create a reproducible scenario showing snapshot replacement.

Example:

### Initial state

Participant A publishes:

```text
Dataset A
Dataset B
```

Catalog displays both.

SPARQL returns the expected results.

### Update

Change Participant A catalog to version 2:

```text
Dataset A gets new Construct-DCAT semantic anchor
Dataset B removed or modified
Dataset C added
```

Republish.

Expected central behavior:

```text
old participant named graph
      ↓
replace
      ↓
new participant named graph
```

No stale triples from the old catalog should remain.

Other participants' graphs must remain unchanged.

Provide an automated integration test for this behavior.

---

# 10. Phase 7 — Semantic Model Graph Prototype

This is a second-stage capability. Keep it separate from the basic live-catalog milestone.

Goal:

Demonstrate that catalog metadata can link to richer semantic graphs and that SPARQL can join them.

Do NOT copy semantic model triples into the participant's catalog graph.

Use separate named graphs.

Example:

```text
GRAPH urn:catalog:<participant>
GRAPH urn:model:<participant>:model-1
```

Catalog graph contains a link to the semantic-model graph/resource.

Semantic-model graph contains domain RDF.

Then demonstrate a cross-graph query:

```sparql
SELECT ?dataset ?entity ?type
WHERE {
  GRAPH ?catalogGraph {
    ?dataset a dcat:Dataset ;
             <semantic-model-link-property> ?model .
  }

  GRAPH ?model {
    ?entity a ?type .
  }
}
```

Use a proper stable graph/resource mapping rather than relying on accidental URI equality.

Document clearly that this is:

```text
cross-named-graph querying inside one Fuseki RDF dataset
```

and NOT yet distributed SPARQL federation.

---

# 11. Out of Scope for Initial Live Demo

Do not spend Phase-1 effort implementing these unless they become required blockers:

- full EDC implementation;
- Kubernetes;
- high availability;
- multiple physical Solid servers;
- distributed transaction handling;
- production-scale authorization architecture;
- automatic crawler over arbitrary Solid Pods;
- full RDF synchronization engine;
- SPARQL `SERVICE` federation;
- remote SPARQL endpoints for every participant;
- reasoning/inference engine;
- complicated message brokers;
- Kafka;
- microservice decomposition;
- automatic semantic-model synchronization.

Keep the initial live demonstrator small, inspectable, and reproducible.

---

# 12. Recommended Demo Deployment

Final Phase-1 topology:

```text
TMDT Solid infrastructure
│
├── Participant Pod A
│      └── catalog/cat.ttl
│
├── Participant Pod B
│      └── catalog/cat.ttl
│
├── Participant C / unregistered WebID
│
└── Registry container

           ▲
           │ Solid-OIDC
           │
     Publisher web app
           │
           │ HTTPS POST
           ▼

Supervisor-provided Linux VM
│
├── reverse proxy / HTTPS
│
├── Federated Catalog
│      ├── /catalog
│      ├── /datasets
│      ├── /datasets/detail
│      ├── /sparql
│      ├── /status
│      └── web UI
│
└── Fuseki/TDB2
       ├── urn:catalog:<participant A>
       ├── urn:catalog:<participant B>
       └── later: semantic-model graphs
```

---

# 13. Demonstration Script

The finished system should support this presentation without manual database editing.

### Demo 1 — federation

1. Open federated catalog.
2. Show empty or existing participant state.
3. Log into Participant A via publisher.
4. Load Participant A's Solid catalog.
5. Preview RDF.
6. Publish.
7. Show accepted response.
8. Open central catalog.
9. Dataset appears.

### Demo 2 — second participant

1. Authenticate as Participant B.
2. Publish different catalog.
3. Central catalog now displays datasets from both providers.
4. Named-graph provenance remains distinguishable.

### Demo 3 — SPARQL

Run one query across all participant graphs.

Show that one query discovers datasets belonging to different participants.

### Demo 4 — Construct-DCAT

Run semantic discovery query.

Show datasets retrieved because of semantic anchors rather than only textual keyword matching.

### Demo 5 — update propagation

1. Modify Participant A catalog.
2. Republish.
3. Refresh catalog/SPARQL query.
4. Results change.
5. Old Participant A triples are no longer present.
6. Participant B remains unchanged.

### Demo 6 — validation

Publish intentionally invalid RDF/DCAT.

Expected result:

```text
422
stage = validation
```

Existing valid Participant A graph must remain unchanged.

### Demo 7 — registry control

Attempt to publish as unregistered participant.

Expected:

```text
403
stage = registry
```

---

# 14. Testing Requirements

Add automated tests wherever reasonably possible.

Minimum integration coverage:

```text
registered + valid publication → accepted

unregistered publication → 403

invalid SHACL publication → 422

valid publication → named graph created

second publication same participant → graph replaced

second participant publication → separate graph retained

container restart → Fuseki data persists

/datasets → correct cross-participant results

/sparql SELECT → correct results

/sparql ASK → correct result

SPARQL UPDATE → rejected

malformed SPARQL → controlled 4xx response
```

Do not make external TMDT services mandatory for ordinary unit tests.

Separate:

```text
unit tests
local integration tests
external TMDT end-to-end tests
```

---

# 15. Documentation Deliverables

Update README/documentation so another TMDT researcher can deploy and operate the demonstrator without reading the source code.

Required documents:

```text
README.md
docs/DEPLOYMENT.md
docs/LIVE_DEMO.md
docs/ARCHITECTURE.md
docs/SPARQL.md
```

`DEPLOYMENT.md` should include:

- Linux prerequisites;
- Docker requirements;
- environment configuration;
- DNS;
- HTTPS;
- persistent volumes;
- startup;
- shutdown;
- backup considerations;
- logs;
- health checks;
- updating the application.

`LIVE_DEMO.md` should contain the exact demonstration sequence.

`ARCHITECTURE.md` should explicitly distinguish:

```text
participant Pod
publisher
registry
federated catalog
Fuseki materialized index
semantic-model graph
```

and distinguish future distributed SPARQL federation from current materialized querying.

---

# 16. Definition of Done — Initial Live Demonstrator

Phase 1 is complete when:

1. The federated catalog runs persistently on a remote Linux server.
2. It is accessible through HTTPS at a stable URL.
3. Fuseki data survives container restarts.
4. At least two real Solid identities/Pods can participate.
5. Membership comes from an external Solid registry.
6. Publisher can read a real Solid catalog and publish it remotely.
7. Registry rejection works.
8. SHACL rejection works.
9. Successful publication creates/replaces participant named graph.
10. Catalog UI displays datasets from multiple participants.
11. User-facing read-only SPARQL querying works.
12. A Construct-DCAT semantic query works across participant catalog graphs.
13. Republishing changed metadata visibly changes query results.
14. The whole demo is documented and reproducible.
15. No direct manual modification of Fuseki is required during the presentation.

---

# 17. Implementation Priority

Execute in this order:

```text
P0  audit current code/tests
P1  persistent production Docker deployment
P2  remote HTTPS catalog
P3  existing TMDT registry + Pods
P4  publisher remote integration
P5  strict Solid-OIDC verification
P6  read-only SPARQL API
P7  SPARQL UI
P8  Construct-DCAT demo data
P9  live update scenario
P10 semantic-model named-graph prototype
```

Do not begin P10 before P0–P9 are stable.

---

# 18. Codex Working Rules

When implementing:

- inspect current code before adding new abstractions;
- preserve existing architecture where it already satisfies the requirement;
- avoid unnecessary rewrites;
- keep Solid and EDC modes separated according to the existing design;
- do not accidentally make the unfinished EDC mode appear operational;
- maintain backwards compatibility for existing local demo workflow;
- add tests alongside behavior changes;
- keep production secrets outside Git;
- document assumptions that depend on TMDT infrastructure;
- flag uncertain Solid-OIDC behavior rather than faking successful authentication;
- use actual Construct-DCAT vocabulary definitions available in the project rather than inventing predicates;
- commit changes in logically separable units where possible.

The immediate milestone is not "solve decentralized semantic federation."

The immediate milestone is:

> **A real, persistent, externally hosted Solid federated metadata catalog that accepts authenticated publications from existing TMDT Solid participants, validates and indexes Construct-DCAT metadata, supports cross-participant discovery and read-only SPARQL querying, and visibly reflects participant updates.**