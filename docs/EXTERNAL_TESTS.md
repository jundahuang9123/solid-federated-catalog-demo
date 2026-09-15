# External TMDT acceptance — pending

These checks require real infrastructure and are intentionally separate from ordinary unit tests. No real identity, Pod, registry membership or remote server has been provisioned by this repository.

Fill in non-secret operational values:

| Field | Value |
| --- | --- |
| Deployment commit | pending |
| Server OS / architecture | pending |
| Catalog HTTPS origin | pending |
| Publisher HTTPS origin | pending |
| Exact TMDT issuer | pending |
| Expected token audience | pending |
| Registry container URL | pending |
| A WebID / Pod catalog URL | pending |
| B WebID / Pod catalog URL | pending |
| Unregistered C WebID | pending |

- [ ] Certificate trusted by a browser; HTTP redirects to HTTPS; no public 8000/3030 ports.
- [ ] Registry and member resources are readable from the catalog server without inventing a new registry service.
- [ ] Participant WebIDs are controlled by the expected TMDT issuer. Confirm issuer authority/ownership assumptions with TMDT; this demo pins one trusted provider and does not implement general WebID issuer discovery.
- [ ] Publisher login/redirect succeeds on its real HTTPS origin.
- [ ] A and B load RDF from their real Pods, not only local fixtures.
- [ ] Existing request-capture tooling shows DPoP-bound authentication material for the intended destination; captures contain no reusable raw tokens in committed evidence.
- [ ] Catalog accepts actual A and B publications with strict OIDC/DPoP enabled. Verify issuer, audience, cnf.jkt, ath, htu, htm and signature compatibility; do not weaken validation to make a demonstration pass.
- [ ] Third unregistered identity receives 403 at registry stage.
- [ ] Invalid fixture receives 422 at validation stage; previous snapshot survives.
- [ ] A update removes old triples; B remains unchanged; Construct-DCAT query changes as documented.
- [ ] Server/container recreation retains Fuseki data; `/ready` recovers.
- [ ] Repeat dependency audit before the public demonstration (the preparation-time npm audit reports zero advisories; see AUDIT.md).

For repeatable local integration, run `python3 scripts/integration_test.py`; it does not prove any box involving TMDT or HTTPS. If the provider issues opaque tokens or uses incompatible token claims/nonce behavior, record the actual mismatch and adapt the verifier/publisher with tests before proceeding.
