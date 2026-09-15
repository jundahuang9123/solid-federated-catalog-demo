#!/usr/bin/env python3
"""Validate operator inputs without printing secrets. Run from repository root."""
from pathlib import Path
import re
import sys

if not Path('.env').is_file():
    print('Create .env first: copy .env.example to .env, then fill in your server and TMDT settings.')
    sys.exit(2)

values = {}
for line in Path('.env').read_text().splitlines():
    if line.strip() and not line.lstrip().startswith('#') and '=' in line:
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip().strip('\"').strip("'")
errors = []
for key in ('CATALOG_HOST', 'PUBLISHER_HOST', 'ACME_EMAIL', 'FUSEKI_PASSWORD',
            'SOLID_REGISTRY_URL', 'SOLID_OIDC_ISSUER'):
    value = values.get(key, '')
    if not value or 'REPLACE' in value or 'example.org' in value:
        errors.append(f'{key}: replace the placeholder')
for key in ('CATALOG_HOST', 'PUBLISHER_HOST'):
    if not re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?', values.get(key, '')):
        errors.append(f'{key}: use a DNS hostname without a protocol, port or path')
if values.get('CATALOG_HOST') == values.get('PUBLISHER_HOST'):
    errors.append('Catalog and publisher need distinct hostnames')
if not re.fullmatch(r'[a-fA-F0-9]{48,}', values.get('FUSEKI_PASSWORD', '')):
    errors.append('FUSEKI_PASSWORD: use at least 24 random bytes encoded as hexadecimal')
for key in ('SOLID_REGISTRY_URL', 'SOLID_OIDC_ISSUER'):
    if not values.get(key, '').startswith('https://'):
        errors.append(f'{key}: HTTPS is required')
if errors:
    print('\n'.join(errors))
    sys.exit(1)
print('Configuration fields look ready. DNS, network reachability and Solid login still need live checks.')
