# Federated Solid Catalog — Live Demonstrator

One repository for the central catalog and participant publisher, based on the existing prototypes. The central service indexes validated metadata from external Solid Pods; it does not host participant Pods or own their original data.

**Status: implementation prepared; remote deployment and real TMDT Solid-OIDC verification are pending.** This is a demonstrator, not a claim of completed production authentication. See [audit and verification status](docs/AUDIT.md) and [external acceptance checklist](docs/EXTERNAL_TESTS.md).

## Included

- `catalog/`: existing FastAPI/Solid pipeline, registry contract, SHACL validation, discovery API/UI and EDC stub.
- `publisher/`: existing Solid login, Pod/local RDF loading, preview and configurable remote publication.
- Root `docker-compose.yml`: catalog + persistent Fuseki/TDB2 + Caddy HTTPS and built publisher. Only ports 80/443 are published.
- Read-only `POST /sparql` for SELECT/ASK; query examples and results UI.
- Deterministic BIM/IFC and AAS metadata using the real Construct-DCAT vocabulary.
- Snapshot replacement through one Graph Store PUT, fail-closed membership refresh, DPoP binding/replay checks, and deployment configuration guards.

## Deploy when the server is available

```bash
git clone https://github.com/jundahuang9123/solid-federated-catalog-demo.git
cd solid-federated-catalog-demo
cp .env.example .env
# Fill in the two DNS hostnames, external TMDT URLs, email and a random password.
python3 scripts/check_config.py
docker compose up -d --build
```

This private repository requires your normal GitHub authentication to clone. Set up DNS before starting Caddy. Do not use example URLs for a live run.

Open `https://<CATALOG_HOST>` and `https://<PUBLISHER_HOST>`. Both hostnames may point to the same server. The publisher is a static browser application served by Caddy; the server still does not contain a Solid Pod service.

## What to obtain from the supervisor

- Linux server access: hostname/IP, SSH username and permitted authentication method, OS and CPU architecture, Docker/Compose availability, available memory and disk.
- Two DNS names pointing to that server, and permission to expose ports 80/443 (or details of an institutional HTTPS proxy).
- Exact TMDT Solid-OIDC issuer URL, registry container URL and whether the registry is publicly readable.
- Two controlled participant WebIDs/Pods, and ideally a third unregistered test identity. Confirm ability to create/update `catalog/cat.ttl` and authorize the publisher origin.

Keep passwords and private keys outside Git and chat. [DEPLOYMENT.md](docs/DEPLOYMENT.md) explains each configuration field and a suggested small-VM starting point.

## Run verification

```bash
python3 -m venv .venv
.venv/bin/pip install -e './catalog[dev]'
(cd catalog && ../.venv/bin/pytest -q)
(cd publisher && npm ci && npm test && npm run build && npm run lint)
# Requires a running Docker engine; uses an isolated disposable test project:
python3 scripts/integration_test.py
```

Use Node 22 for publisher work. Unit tests do not contact TMDT. The integration script starts a small registry fixture (not a Solid server), exercises actual Fuseki, recreates containers without deleting data, then removes its own isolated test volume. GitHub Actions runs these jobs on pushes.

For the original local workflows, see the component READMEs. Their Compose files are local development examples, not the root production deployment.

## Documentation

- [Deployment and server handover](docs/DEPLOYMENT.md)
- [Live demonstration sequence](docs/LIVE_DEMO.md)
- [Architecture and trust boundaries](docs/ARCHITECTURE.md)
- [Read-only SPARQL](docs/SPARQL.md)
- [External TMDT acceptance](docs/EXTERNAL_TESTS.md)
- [Original requirements](docs/REQUIREMENTS.md)

## Attribution

Original catalog: [Dual-Federated-Catalog-Solid-EDC-](https://github.com/jundahuang9123/Dual-Federated-Catalog-Solid-EDC-), commit `632e735a50a2a709cd31a10be33aae5a0ab12bd2`.
Original publisher: [solid-federated-catalog-publisher](https://github.com/jundahuang9123/solid-federated-catalog-publisher), commit `6485e30c8daaafcdc4b1de2a6e3f712f48dc025e`.
[ConstructDCAT](https://github.com/jundahuang9123/ConstructDCAT), version 0.1.0, commit `2effb755897b99342f8405afac96425f6c13649c` (Junda Huang, CC BY 4.0), supplies the vocabulary referenced by the fixtures.

The component LICENSE, NOTICE and CREDITS files retain upstream attribution, including Florian Hoelken et al.'s semantic-data-catalog work. EDC remains explicitly non-operational; semantic-model graph ingestion is deferred until the live catalog milestone is stable.
