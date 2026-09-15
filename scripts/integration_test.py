#!/usr/bin/env python3
"""Owns an isolated Compose project; destroys ONLY that project's test volume."""
import json
from http.client import RemoteDisconnected
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
PROJECT = 'catalog-test-' + uuid4().hex[:10]
COMPOSE = ['docker', 'compose', '-p', PROJECT, '-f', 'docker-compose.integration.yml']
A, B = [f'https://pod.example/{name}/profile/card#me' for name in ('a', 'b')]
base = ''


def compose(*args):
    return subprocess.run(COMPOSE + list(args), cwd=ROOT, check=True, capture_output=True, text=True).stdout


def request(path, body=None, participant=None):
    headers = {}
    if isinstance(body, dict):
        body = json.dumps(body).encode()
        headers['Content-Type'] = 'application/json'
    elif body is not None:
        headers['Content-Type'] = 'text/turtle'
    if participant:
        headers['X-Participant-Id'] = participant
    try:
        with urlopen(Request(base + path, data=body, headers=headers), timeout=30) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


def wait_ready():
    global base
    base = 'http://' + compose('port', 'catalog', '8000').strip()
    for attempt in range(90):
        try:
            if request('/ready')[0] == 200:
                return
        except (URLError, TimeoutError, ConnectionError, RemoteDisconnected):
            pass
        time.sleep(2)
    raise RuntimeError('Catalog did not become ready')


def publish(who, fixture):
    return request('/catalog', (ROOT / 'demo-data' / fixture).read_bytes(), who)


def query(text):
    code, result = request('/sparql', {'query': text})
    assert code == 200, result
    return result


def graph_snapshot(who):
    from urllib.parse import quote
    graph = 'urn:catalog:' + quote(who, safe='')
    rows = query(f'SELECT ?s ?p ?o WHERE {{ GRAPH <{graph}> {{ ?s ?p ?o }} }}')['results']['bindings']
    return {json.dumps(row, sort_keys=True) for row in rows}


if __name__ == '__main__':
    try:
        print(f'Starting disposable integration project {PROJECT}', flush=True)
        compose('up', '-d', '--build')
        wait_ready()
        assert publish(A, 'participant-a/catalog-v1.ttl')[0] == 200
        assert publish(B, 'participant-b/catalog-v1.ttl')[0] == 200
        assert len(request('/datasets')[1]) == 3
        assert request('/datasets/detail?dataset_id=https%3A%2F%2Fexample.org%2Flive-demo%2Fa-frame')[0] == 200
        walls = (ROOT / 'demo-data/queries/walls.rq').read_text()
        assert len(query(walls)['results']['bindings']) == 2
        b_before = graph_snapshot(B)
        assert publish(A, 'participant-a/catalog-v2.ttl')[0] == 200
        a_after = graph_snapshot(A)
        assert graph_snapshot(B) == b_before
        assert not any('a-slabs' in row for row in a_after)
        assert len(query(walls)['results']['bindings']) == 3
        status, payload = publish(A, 'invalid/invalid-catalog.ttl')
        assert status == 422 and payload['stage'] == 'validation'
        assert graph_snapshot(A) == a_after
        status, payload = publish('https://unregistered.example/me', 'participant-b/catalog-v1.ttl')
        assert status == 403 and payload['stage'] == 'registry'
        assert query('ASK {}')['boolean'] is True
        for unsafe in ['DROP ALL', 'SELECT ???', 'SELECT * WHERE { SERVICE <http://example.org> { ?s ?p ?o } }']:
            assert request('/sparql', {'query': unsafe})[0] == 400
        compose('stop', 'registry')
        status, payload = publish(A, 'participant-a/catalog-v1.ttl')
        assert status == 422 and payload['stage'] == 'registry'
        assert graph_snapshot(A) == a_after
        assert request('/ready')[0] == 503
        print('Recreating all containers; retaining the named volume', flush=True)
        compose('down')
        compose('up', '-d')
        wait_ready()
        assert len(request('/datasets')[1]) == 3
        assert graph_snapshot(A) == a_after
        assert graph_snapshot(B) == b_before
        assert len(query(walls)['results']['bindings']) == 3
        print('PASS: registry, SHACL, discovery, SPARQL, isolation, replacement and restart persistence')
    except Exception:
        try:
            print(compose('logs', '--tail=80'))
        except Exception:
            pass
        raise
    finally:
        print(f'Removing isolated test project {PROJECT}', flush=True)
        compose('down', '--volumes', '--remove-orphans')
