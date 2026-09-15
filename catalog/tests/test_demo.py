"""Real RDF queries behind the real HTTP client, with an in-memory index transport."""
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi.testclient import TestClient
from rdflib import Dataset, Graph, URIRef
from rdflib.compare import isomorphic

from core.shared.fuseki import FusekiClient, FusekiSettings
from core.shared.shacl_validate import ShaclValidationGate
from modes.solid.auth import TrustedHeaderSolidAuth
from modes.solid.discovery import SolidDiscovery
from modes.solid.ingest import SolidIngest
from modes.solid.store import SolidStore, graph_uri_for_participant
from tests.fixtures import FakeRegistry

DATA = Path(__file__).resolve().parents[2] / 'demo-data'
A = 'https://pod.example/a/profile/card#me'
B = 'https://pod.example/b/profile/card#me'


@pytest.fixture
def system(monkeypatch):
    monkeypatch.setenv('CATALOG_MODE', 'solid')
    monkeypatch.setenv('CATALOG_STARTUP_CHECKS', 'false')
    monkeypatch.delenv('CATALOG_PUBLIC_URL', raising=False)
    dataset = Dataset()
    calls = []

    def handler(request):
        calls.append(request)
        if request.method == 'PUT':
            graph = URIRef(request.url.params['graph'])
            replacement = Graph().parse(data=request.content, format='turtle')
            dataset.graph(graph).remove((None, None, None))
            for triple in replacement:
                dataset.graph(graph).add(triple)
            return httpx.Response(204)
        query = parse_qs(request.content.decode())['query'][0]
        result = dataset.query(query)
        return httpx.Response(200, content=result.serialize(format='json'))

    fuseki = FusekiClient(FusekiSettings('http://index/solid'), http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    store = SolidStore(fuseki)
    registry = FakeRegistry({A, B})
    mode = SimpleNamespace(name='solid', store=store, discovery=SolidDiscovery(store, registry),
                           ingest=SolidIngest(registry, ShaclValidationGate(), store, TrustedHeaderSolidAuth()))
    from core import app as module
    monkeypatch.setattr(module, 'load_active_mode', lambda: mode)
    with TestClient(module.create_app()) as client:
        yield client, dataset, calls


def publish(client, participant, path):
    return client.post('/catalog', content=(DATA / path).read_bytes(),
                       headers={'Content-Type': 'text/turtle', 'X-Participant-Id': participant})


def test_live_update_validation_discovery_and_semantic_query(system):
    client, index, calls = system
    assert publish(client, A, 'participant-a/catalog-v1.ttl').status_code == 200
    assert publish(client, B, 'participant-b/catalog-v1.ttl').status_code == 200
    b_before = Graph()
    for triple in index.graph(URIRef(graph_uri_for_participant(B))):
        b_before.add(triple)
    model = index.graph(URIRef('urn:model:demo:reserved'))
    model.add((URIRef('urn:entity'), URIRef('urn:property'), URIRef('urn:value')))
    wall_query = (DATA / 'queries/walls.rq').read_text()
    assert len(client.post('/sparql', json={'query': wall_query}).json()['results']['bindings']) == 2
    assert len(client.get('/datasets').json()) == 3
    assert client.get('/datasets/detail', params={'dataset_id': 'https://example.org/live-demo/a-frame'}).status_code == 200
    assert publish(client, A, 'participant-a/catalog-v2.ttl').status_code == 200
    rows = client.get('/datasets').json()
    assert len(rows) == 3
    assert not any(row['dataset_id'].endswith('a-slabs') for row in rows)
    assert any(row['title'] == 'Frame export — revision 2' for row in rows)
    assert isomorphic(b_before, index.graph(URIRef(graph_uri_for_participant(B))))
    assert len(model) == 1
    assert len(client.post('/sparql', json={'query': wall_query}).json()['results']['bindings']) == 3
    a_before = set(index.graph(URIRef(graph_uri_for_participant(A))))
    invalid = publish(client, A, 'invalid/invalid-catalog.ttl')
    assert invalid.status_code == 422 and invalid.json()['stage'] == 'validation'
    assert set(index.graph(URIRef(graph_uri_for_participant(A)))) == a_before
    rejected = publish(client, 'https://unregistered.example/me', 'participant-b/catalog-v1.ttl')
    assert rejected.status_code == 403 and rejected.json()['stage'] == 'registry'
    assert all(request.method != 'DELETE' for request in calls)


@pytest.mark.parametrize('query', [
    'INSERT DATA { <urn:s> <urn:p> <urn:o> }', 'DELETE WHERE { ?s ?p ?o }',
    'DROP ALL', 'LOAD <http://example.org/file>', 'CLEAR ALL', 'CREATE GRAPH <urn:g>',
    'MOVE DEFAULT TO GRAPH <urn:g>', 'COPY DEFAULT TO GRAPH <urn:g>', 'ADD DEFAULT TO GRAPH <urn:g>',
    'SELECT * WHERE { SERVICE <http://localhost:3030/> { ?s ?p ?o } }',
    'SELECT * WHERE { { SELECT * WHERE { SERVICE SILENT <http://example.org> { ?s ?p ?o } } } }',
    'SELECT * FROM <http://example.org/a> WHERE { ?s ?p ?o }',
    'SELECT (<http://example.org/function>("x") AS ?x) WHERE {}',
    'SELECT ???', 'PREFIX bad: <urn:bad> SELECT ?s WHERE { ?s unknown:p ?o }',
    'CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }',
])
def test_unsafe_or_malformed_queries_never_reach_fuseki(system, query):
    client, _, calls = system
    before = len(calls)
    assert client.post('/sparql', json={'query': query}).status_code == 400
    assert len(calls) == before


def test_query_json_terms_ask_and_limits(system):
    client, _, _ = system
    response = client.post('/sparql', json={'query': 'SELECT ("bonjour"@fr AS ?label) (42 AS ?n) WHERE {}'})
    assert response.status_code == 200
    binding = response.json()['results']['bindings'][0]
    assert binding['label']['xml:lang'] == 'fr'
    assert binding['n']['datatype'].endswith('#integer')
    assert client.post('/sparql', json={'query': 'ASK { GRAPH <urn:missing> { ?s ?p ?o } }'}).json()['boolean'] is False
    assert client.post('/sparql', json={'query': 'ASK {}'}).json()['boolean'] is True
    values = ' '.join(str(n) for n in range(600))
    rows = client.post('/sparql', json={'query': f'SELECT ?n WHERE {{ VALUES ?n {{ {values} }} }}'}).json()['results']['bindings']
    assert len(rows) == 500
    assert client.post('/sparql', content=b'x'*32769).status_code == 413
    assert client.post('/sparql', content=b'not JSON').status_code == 400
    assert client.post('/sparql', json={'query': 5}).status_code == 400


def test_literal_update_word_is_not_rejected(system):
    client, _, _ = system
    assert client.post('/sparql', json={'query': '# SELECT\nPREFIX ex: <urn:SELECT>\nSELECT ("DELETE SERVICE" AS ?text) WHERE {}'}).status_code == 200


def test_failed_put_does_not_send_delete():
    calls = []
    def handler(request):
        calls.append(request.method)
        return httpx.Response(500)
    client = FusekiClient(FusekiSettings('http://index/solid'), http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(RuntimeError):
        client.replace_named_graph('urn:catalog:a', '<urn:s> <urn:p> <urn:o> .')
    assert calls == ['PUT']


@pytest.mark.parametrize('kind,expected', [('timeout', 504), ('network', 502), ('oversize', 502), ('syntax', 400)])
def test_query_backend_failures_are_controlled(system, monkeypatch, kind, expected):
    client, _, _ = system
    def fail(*args, **kwargs):
        if kind == 'timeout':
            raise httpx.ReadTimeout('timeout')
        if kind == 'network':
            raise httpx.ConnectError('unavailable')
        if kind == 'syntax':
            response = httpx.Response(400, request=httpx.Request('POST', 'http://index/query'))
            response.raise_for_status()
        raise ValueError('Response limit exceeded')
    monkeypatch.setattr(FusekiClient, 'query_results', fail)
    assert client.post('/sparql', json={'query': 'ASK {}'}).status_code == expected
    # A failed query releases its concurrency slot for another request.
    assert client.post('/sparql', json={'query': 'ASK {}'}).status_code == expected
