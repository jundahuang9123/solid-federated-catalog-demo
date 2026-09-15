import base64
import hashlib
import time

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.shared.shacl_validate import ShaclValidationGate
from modes.solid.auth import OidcSolidAuth, jwk_thumbprint
from modes.solid.ingest import SolidIngest
from tests.fixtures import VALID_TURTLE, FakeRegistry, MemoryCatalogStore
from tests.test_solid_auth import ISSUER, REGISTERED_WEBID, _oidc_client, _private_key, _public_jwk


def make_request(token_changes=None, proof_changes=None, header_changes=None):
    access_key, proof_key = _private_key(), _private_key()
    public = _public_jwk(proof_key)
    now = int(time.time())
    claims = dict(iss=ISSUER, iat=now, exp=now+300, webid=REGISTERED_WEBID, cnf={'jkt': jwk_thumbprint(public)})
    claims.update(token_changes or {})
    token = jwt.encode(claims, access_key, algorithm='RS256', headers={'kid': 'test'})
    ath = base64.urlsafe_b64encode(hashlib.sha256(token.encode()).digest()).rstrip(b'=').decode()
    proof = dict(htu='http://testserver/catalog', htm='POST', iat=now, jti='proof-1', ath=ath)
    proof.update(proof_changes or {})
    header = {'typ': 'dpop+jwt', 'jwk': public}
    header.update(header_changes or {})
    dpop = jwt.encode(proof, proof_key, algorithm='RS256', headers=header)
    auth = OidcSolidAuth(issuer=ISSUER, http_client=_oidc_client(_public_jwk(access_key, kid='test')))
    app = FastAPI()
    app.include_router(SolidIngest(FakeRegistry({REGISTERED_WEBID}), ShaclValidationGate(), MemoryCatalogStore(), auth).routes())
    return TestClient(app), {'Authorization': f'DPoP {token}', 'DPoP': dpop, 'Content-Type': 'text/turtle'}


@pytest.mark.parametrize('token,proof,header', [
    ({'cnf': {}}, {}, {}), ({'cnf': {'jkt': 'wrong'}}, {}, {}),
    ({'iss': 'https://attacker.example'}, {}, {}), ({'exp': 1}, {}, {}),
    ({}, {'ath': 'wrong'}, {}), ({}, {'ath': None}, {}),
    ({}, {'htu': 'https://wrong.example/catalog'}, {}), ({}, {'htm': 'GET'}, {}),
    ({}, {'iat': 1}, {}), ({}, {'jti': ''}, {}), ({}, {}, {'typ': 'JWT'}),
])
def test_invalid_auth_is_401(token, proof, header):
    client, headers = make_request(token, proof, header)
    response = client.post('/catalog', content=VALID_TURTLE, headers=headers)
    assert response.status_code == 401
    assert response.json()['stage'] == 'auth'


def test_replay_rejected():
    client, headers = make_request()
    assert client.post('/catalog', content=VALID_TURTLE, headers=headers).status_code == 200
    assert client.post('/catalog', content=VALID_TURTLE, headers=headers).status_code == 401


def test_public_url_binding_and_malformed_token(monkeypatch):
    monkeypatch.setenv('CATALOG_PUBLIC_URL', 'https://catalog.example.org')
    client, headers = make_request(proof_changes={'htu': 'https://catalog.example.org/catalog'})
    assert client.post('/catalog?participant_id=ignored', content=VALID_TURTLE, headers=headers).status_code == 200
    headers['Authorization'] = 'DPoP malformed'
    assert client.post('/catalog', content=VALID_TURTLE, headers=headers).status_code == 401
