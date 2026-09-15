# Construction demo fixtures

Vocabulary: https://github.com/jundahuang9123/ConstructDCAT at commit `2effb755897b99342f8405afac96425f6c13649c`, version 0.1.0 (CC BY 4.0; Junda Huang). The fixtures use its exact `https://w3id.org/construct-dcat#` terms: `BIMDataset`, `AASDataset`, `describesAssetType`, `usesOntology`, `hasAASSubmodel`.

Participant A supplies IFC metadata; B supplies AAS metadata. Their titles deliberately do not contain “wall”. Both use `cx:describesAssetType ifc:IfcWall`; the query works through the semantic anchor, without inference or keyword matching. All datasets also explicitly have `dcat:Dataset` type.

A v1 has frame and slab datasets. A v2 updates the frame title, removes slabs, and adds panels carrying a wall anchor. B remains unchanged. Query wall counts: 2 before and 3 after A's update. Dataset counts: 3 before and 3 after.

The example.org resource IDs and download URLs are deterministic illustrative metadata, not hosted files or real participant WebIDs. The authenticated publisher determines graph ownership. Copy each fixture into its real Pod at `catalog/cat.ttl`; the operator can replace example distribution URLs with controlled resources before the real presentation. No data file contents are copied into the central index.
