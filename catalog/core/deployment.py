"""Reject development settings in the public deployment."""
import os
from urllib.parse import urlsplit


def validate_deployment():
    if os.getenv('CATALOG_DEPLOYMENT') != 'production':
        return
    required = {'CATALOG_MODE': 'solid', 'SOLID_AUTH_MODE': 'oidc', 'SOLID_AUTH_REQUIRE_DPOP': 'true'}
    for key, value in required.items():
        if os.getenv(key, '').lower() != value:
            raise RuntimeError(f'{key} must be {value} for the production demonstrator')
    for key in ('SOLID_REGISTRY_URL', 'SOLID_OIDC_ISSUER', 'CATALOG_PUBLIC_URL'):
        value = os.getenv(key, '')
        parsed = urlsplit(value)
        if parsed.scheme != 'https' or not parsed.hostname or 'REPLACE' in value or parsed.username:
            raise RuntimeError(f'{key} must be configured with an HTTPS URL')
    public = urlsplit(os.environ['CATALOG_PUBLIC_URL'])
    if public.path not in ('', '/') or public.query or public.fragment:
        raise RuntimeError('CATALOG_PUBLIC_URL must be an origin without a path, query or fragment')
    if not os.getenv('SOLID_OIDC_AUDIENCE'):
        raise RuntimeError('SOLID_OIDC_AUDIENCE is required in production')
    origins = os.getenv('CATALOG_CORS_ORIGINS', '')
    if not origins or '*' in origins or any(not item.strip().startswith('https://') for item in origins.split(',')):
        raise RuntimeError('Production CORS origins must explicitly use HTTPS')
    password = os.getenv('FUSEKI_PASSWORD', '')
    if len(password) < 24 or 'REPLACE' in password or not all(c in '0123456789abcdefABCDEF' for c in password):
        raise RuntimeError('Configure a long random hexadecimal Fuseki password')
