# Deployment and server handover

## Planned topology

One Linux VM runs Docker Compose. Caddy serves the built publisher and proxies catalog requests. Fuseki uses a named volume and an internal network. Solid Pods, identities and the registry stay on existing TMDT infrastructure.

A reasonable small-demo starting point is 2 vCPUs, 4 GB RAM and 20 GB of persistent disk, to be adjusted after measurement. This is a planning estimate, not a tested capacity guarantee. Ask the supervisor whether the VM is amd64 or arm64 and whether outbound internet access is restricted. The catalog needs access to the registry and configured issuer/JWKS; builds need package and container registries.

## Prerequisites

- Linux with Docker Engine and Docker Compose v2 (`docker compose version`). Follow your institution's installation policy.
- SSH access with permission to use Docker. Python 3 is useful for the configuration check and test script.
- Two DNS A/AAAA records, e.g. `catalog.example.org` and `publisher.example.org`, directed to the VM. Avoid an AAAA record unless IPv6 works.
- Inbound TCP 80/443 to Caddy for automatic certificates and HTTPS. Do not open 8000 or 3030.
- Exact external TMDT URLs and controlled participants; confirm the issuer's expected `aud` and JWT/DPoP support.

If the supervisor provides an institutional reverse proxy, a subpath-only URL, private-only DNS, or a server without Docker, this deployment needs adaptation. Do not guess or disable certificate verification. The provided layout expects two HTTPS origins without URL subpaths.

## Environment

Copy `.env.example` to `.env`, restrict its filesystem permissions (`chmod 600 .env`), and replace placeholders. It contains no working secrets.

| Setting | Meaning |
| --- | --- |
| `CATALOG_HOST` | Catalog DNS name, no scheme/path |
| `PUBLISHER_HOST` | Publisher DNS name, different from catalog |
| `ACME_EMAIL` | Operator contact for TLS certificate management |
| `FUSEKI_PASSWORD` | Generate with `openssl rand -hex 32`; save only in `.env` |
| `FUSEKI_IMAGE` | Default `stain/jena-fuseki:5.1.0`; review image updates before use |
| `SOLID_REGISTRY_URL` | Actual readable TMDT LDP registry container |
| `SOLID_REGISTRY_CONTRACT_PATH` | Container path `config/solid-registry-contract.yaml`; keep unless contract changes |
| `SOLID_REGISTRY_CACHE_TTL_SECONDS` | Default 0 rechecks publication membership; positive values introduce that much revocation delay; expired caches fail closed |
| `SOLID_OIDC_ISSUER` | Exact trusted provider issuer, including trailing slash if present |
| `SOLID_OIDC_AUDIENCE` | Expected audience; defaults to `solid`; confirm with actual TMDT tokens |
| `SPARQL_*` | Request, row, response-byte and application timeout bounds |

Root Compose fixes `CATALOG_MODE=solid`, `SOLID_AUTH_MODE=oidc`, `SOLID_AUTH_REQUIRE_DPOP=true`, `FUSEKI_URL=http://fuseki:3030/solid` and `FUSEKI_USER=admin`. It derives `CATALOG_PUBLIC_URL` and `CATALOG_CORS_ORIGINS` from the hostnames. Those URL fields in `.env.example` also document the variables used when running the application directly.

Compose builds the publisher with the public catalog's full `/catalog` URL and the same issuer. Changing those values requires rebuilding the reverse-proxy image. The UI still permits a participant to choose another target. Use only the intended controlled endpoint for authenticated publications.

Do not put passwords in `VITE_*` variables: these are included in browser assets. Never paste access tokens into Git or issue reports. The publisher's manual bearer-token override is a development tool, not the production DPoP path.

## Start and verify

```bash
python3 scripts/check_config.py
docker compose config --quiet
docker compose up -d --build
docker compose ps
curl --fail https://<CATALOG_HOST>/health
curl --fail https://<CATALOG_HOST>/ready
```

`/health` confirms the process is alive; `/ready` checks registry and Fuseki and returns 503 on critical dependency failure. `/status` gives discovery counts and dependency information. Readiness does not prove browser Solid login works; complete [EXTERNAL_TESTS.md](EXTERNAL_TESTS.md).

Caddy provides TLS and forwards host/protocol information. Uvicorn trusts forwarding headers because only the proxy can reach it through the public deployment; the catalog has no published port. Authentication also binds DPoP to the configured public origin. If you change the topology, review those assumptions. Run one catalog process: the bounded replay cache is process-local and resets on restart; it is not a multi-instance authentication design.

The configured trusted issuer is the identity authority for this controlled TMDT demo. Arbitrary token-supplied issuers are rejected. This is not a general WebID-to-provider trust discovery implementation. Live issuer/WebID ownership checks and client compatibility must be confirmed before calling the system complete.

## Persistence, stop and restart

```bash
docker compose down
docker compose up -d
```

The `fuseki-data` named volume mounts `/fuseki`; the assembler stores TDB2 at `/fuseki/databases/solid`. Ordinary `down` retains data and Caddy's certificate volumes. **Do not use `down --volumes` on the live project** unless intentionally discarding all indexed metadata/certificates. Keep the same Compose project name; changing it creates different volumes.

The first Fuseki start writes authentication configuration into its persistent volume. Changing `.env` alone may not rotate the stored admin password. For rotation, stop the stack, back up the volume, follow the image's Shiro configuration procedure, then update the catalog password and restart. Do not remove the data volume to rotate credentials.

## Backup and recovery

For this small demo, schedule a stopped-volume backup rather than copying an active TDB2 database. Stop catalog and Fuseki, archive the named volume with your institution's Docker-volume backup tool, and restart. Record the image version/digest and configuration with the backup. Store `.env` and the persisted Shiro file in restricted backup storage because they contain credentials. Test restore into a separate project/volume before relying on it.

The original metadata remains in participant Pods, so the index can also be rebuilt by authorized republication. This does not replace backups of system configuration or unrelated future model graphs. Never mount the same TDB2 volume into two running Fuseki processes.

## Logs and updates

```bash
docker compose logs --tail=100 catalog fuseki reverse-proxy
git pull --ff-only
docker compose up -d --build
```

Take a backup before an update. Run the unit and disposable integration checks first. Record `git rev-parse HEAD` and `docker compose images`. Pin reviewed image digests for a scheduled presentation once the target platform is verified. A mutable image tag is not a supply-chain reproducibility guarantee.

If readiness fails, check registry permissions/URLs and internal Fuseki health. If publication is 401, inspect the sanitized request capture and issuer/audience/DPoP fields. Never switch the public service to trusted headers to get past an authentication failure.

## References

[Fuseki configuration](https://jena.apache.org/documentation/fuseki2/fuseki-configuration.html), [image persistence and operations](https://github.com/stain/jena-docker/tree/master/jena-fuseki), [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https).
