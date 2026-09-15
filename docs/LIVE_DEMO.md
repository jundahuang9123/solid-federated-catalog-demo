# Live demonstration script

Complete [EXTERNAL_TESTS.md](EXTERNAL_TESTS.md) before calling this a live TMDT demo. Use two separate browser profiles for A and B so sessions cannot be confused. The publisher's token override stays empty.

## Prepare once

1. Deploy the root stack and verify the two HTTPS origins and `/ready`.
2. Obtain two controlled participant WebIDs with Pods on TMDT. Put both WebIDs into the external registry using the existing administrative process. Keep an optional third identity unregistered.
3. Upload `demo-data/participant-a/catalog-v1.ttl` to A's `<Pod root>/catalog/cat.ttl`; upload B's v1 to B's corresponding resource. Use the Pod's normal authenticated file management workflow. The central server does not create these resources.
4. Confirm each participant can read its catalog in the publisher. Fixture URLs at example.org are illustrative metadata, not promised downloadable files; replace them with controlled demo resource URLs if downloads will be demonstrated.
5. Rehearse the request-capture step from `publisher/docs/auth-findings.md` in a controlled environment. The default local catcher is a development diagnostic; a deployed HTTPS publisher may need a controlled HTTPS catcher/proxy because browsers can block mixed content or local-network access. Do not publicly deploy the permissive catcher.
6. Check Authorization scheme, DPoP presence, token `cnf.jkt`, proof `htu`, `htm=POST`, `ath`, public JWK and timestamp. A decoded capture is diagnostic only; then perform the actual push against the real catalog.

## Presentation

### 1. First participant

Open the catalog's Datasets page. In profile A, open the publisher, log into the configured TMDT provider, load `catalog/cat.ttl`, inspect the RDF preview, and publish to `https://<CATALOG_HOST>/catalog`.

Show accepted response with A's authenticated participant ID and encoded named-graph URI. Refresh discovery: “Frame export — revision 1” and “Floor package” appear. Show dataset detail.

### 2. Second participant

In profile B, log in, load B's Pod resource and publish. Refresh discovery: “Component passport set” appears alongside A's two datasets. Run the Participants query to show separate named graphs. Other pre-existing participants may also appear; scope the example query to the two demonstrated graph IRIs if necessary.

### 3. Cross-participant SPARQL

Choose All datasets. Show graph, dataset and title bindings. Choose the construction wall query: it returns A's frame dataset and B's component passports. Their titles do not contain “wall”; discovery uses `cx:describesAssetType ifc:IfcWall` across BIM/AAS representations.

### 4. Snapshot update

Replace A's Pod `catalog/cat.ttl` with `participant-a/catalog-v2.ttl` using the normal Pod write workflow. In publisher A, reload the Pod resource, preview revision 2, and republish.

Refresh discovery: frame revision 2 replaces revision 1, floor package disappears, and envelope package appears. B remains unchanged. The wall query now returns three datasets for these participants. Republish v1 to reset A when needed; no manual database editing is necessary.

### 5. Validation rejection

While logged in as A, load `invalid/invalid-catalog.ttl` through the publisher's local file input and publish. This lacks the required distribution. Show HTTP 422 with `stage=validation`. Refresh discovery to show the valid revision 2 still exists. The invalid fixture need not overwrite the valid Pod resource.

### 6. Membership rejection

Log in as the third unregistered controlled identity. Load valid RDF and attempt publication. Show HTTP 403 with `stage=registry`. Confirm no new graph or dataset appears. A forged participant header must not impersonate a registered identity in the public deployment.

### 7. Persistence (optional during presentation)

After the successful publications, run `docker compose down`, followed by `docker compose up -d`. Wait for readiness and refresh discovery/query. The previous datasets remain. Do not add `--volumes`.

## Record evidence

Record commit ID, URLs, timestamp, participant graph IDs, response status/stage and expected dataset counts. Keep token values, DPoP proofs, credentials and private Pod content out of screenshots or Git commits. Use the acceptance checklist to distinguish observed results from expectations.
