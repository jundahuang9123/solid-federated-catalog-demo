import pytest

from core.deployment import validate_deployment


def test_production_rejects_trusted_headers_and_missing_configuration(monkeypatch):
    monkeypatch.setenv('CATALOG_DEPLOYMENT', 'production')
    monkeypatch.setenv('CATALOG_MODE', 'solid')
    monkeypatch.setenv('SOLID_AUTH_MODE', 'trusted-header')
    with pytest.raises(RuntimeError, match='SOLID_AUTH_MODE'):
        validate_deployment()


def test_complete_production_configuration(monkeypatch):
    settings = {
        'CATALOG_DEPLOYMENT': 'production', 'CATALOG_MODE': 'solid', 'SOLID_AUTH_MODE': 'oidc',
        'SOLID_AUTH_REQUIRE_DPOP': 'true', 'SOLID_OIDC_AUDIENCE': 'solid',
        'SOLID_REGISTRY_URL': 'https://registry.example/container/',
        'SOLID_OIDC_ISSUER': 'https://issuer.example/',
        'CATALOG_PUBLIC_URL': 'https://catalog.example',
        'CATALOG_CORS_ORIGINS': 'https://publisher.example', 'FUSEKI_PASSWORD': 'a'*48,
    }
    for key, value in settings.items():
        monkeypatch.setenv(key, value)
    validate_deployment()
    monkeypatch.setenv('CATALOG_PUBLIC_URL', 'https://catalog.example/subpath')
    with pytest.raises(RuntimeError, match='origin'):
        validate_deployment()
