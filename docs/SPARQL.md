# Read-only SPARQL

Open the SPARQL navigation link in the catalog. Choose an example, edit it, and run. SELECT produces a table; hover over cells to inspect RDF type/datatype/language. ASK reports true/false. All values are rendered as text.

```bash
curl -sS https://<CATALOG_HOST>/sparql \
  -H 'Content-Type: application/json' \
  --data '{"query":"ASK { GRAPH ?g { ?s ?p ?o } }"}'
```

Responses use SPARQL Results JSON (`head.vars`, `results.bindings`, or `boolean`). Each bound term retains `type`, `value`, and any `datatype` / `xml:lang` supplied by Fuseki. Internal discovery can keep flattened strings.

## Boundaries

- SELECT and ASK only; UPDATE, INSERT, DELETE, LOAD, CLEAR, CREATE, DROP, MOVE, COPY and ADD are rejected. CONSTRUCT/DESCRIBE are intentionally not supported yet.
- Parser-based validation rejects remote SERVICE clauses (including nested/SILENT), FROM/FROM NAMED, and custom extension functions. Undefined prefixes and malformed syntax return 400.
- 32 KiB request body, 500 SELECT rows, 2 MiB response, 10-second application timeout, and at most two simultaneous user queries by default. Limit settings are environment-configurable.
- Fuseki also has a server-side 10-second query timeout in `deploy/fuseki.ttl`. Increasing the application timeout does not change that server limit.
- SELECT is wrapped in a limited outer query, preserving projections, aggregates and inner LIMIT/OFFSET. Presentation ordering across the subquery boundary is not guaranteed; the endpoint is for inspection, not stable cursor pagination.
- Literal Unicode is supported; escaped Unicode spellings are rejected to avoid ambiguity in the query wrapper.
- Statuses: 400 bad query/JSON or unsupported operation; 413 oversized request; 429 capacity; 502 backend failure/oversized result; 504 timeout.

Queries can read the central index's named graphs. There is no per-graph read authorization. Publish only metadata intended to be discoverable by all demo visitors.

## Examples

Versioned files: `demo-data/queries/datasets.rq`, `participants.rq`, `walls.rq`, `ask.rq`. The browser copies are in `catalog/ui/queries.json`.

The construction query uses exact terms from ConstructDCAT version 0.1.0:

```sparql
PREFIX cx: <https://w3id.org/construct-dcat#>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX ifc: <https://standards.buildingsmart.org/IFC/DEV/IFC4_3/OWL#>
SELECT ?graph ?dataset WHERE {
  GRAPH ?graph {
    ?dataset a dcat:Dataset ; cx:describesAssetType ifc:IfcWall .
  }
}
```

The fixture's BIM and AAS datasets share the same explicit asset-type IRI. No free-text match, ontology fetch, or inference is needed. Expected wall matches: two after A v1 + B v1, three after A v2 + B v1.
