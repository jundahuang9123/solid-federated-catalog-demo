# Adapted from tmdt-buw/semantic-data-catalog (F. Hoelken et al.), Apache-2.0.
"""Fuseki graph-store and SPARQL helpers."""

from __future__ import annotations

import os
import json
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class FusekiSettings:
    dataset_url: str
    username: str = "admin"
    password: str = "admin"
    timeout_seconds: float = 10.0

    @classmethod
    def from_env(cls) -> "FusekiSettings":
        return cls(
            dataset_url=os.getenv("FUSEKI_URL", "http://localhost:3030/solid"),
            username=os.getenv("FUSEKI_USER", "admin"),
            password=os.getenv("FUSEKI_PASSWORD", "admin"),
            timeout_seconds=float(os.getenv("FUSEKI_TIMEOUT_SECONDS", "10")),
        )


class FusekiClient:
    def __init__(
        self,
        settings: FusekiSettings | None = None,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or FusekiSettings.from_env()
        self.dataset_url = self.settings.dataset_url.rstrip("/")
        self._client = http_client or httpx.Client(timeout=self.settings.timeout_seconds)
        self._owns_client = http_client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _endpoint(self, name: str) -> str:
        if self.dataset_url.endswith(f"/{name}"):
            return self.dataset_url
        return f"{self.dataset_url}/{name}"

    @property
    def _auth(self) -> tuple[str, str]:
        return (self.settings.username, self.settings.password)

    def replace_named_graph(
        self,
        graph_uri: str,
        rdf_payload: str | bytes,
        *,
        content_type: str = "text/turtle",
    ) -> None:
        data_endpoint = self._endpoint("data")
        # Graph Store PUT replaces one graph in one server transaction.
        response = self._client.put(
            data_endpoint,
            params={"graph": graph_uri},
            headers={"Content-Type": content_type},
            content=rdf_payload,
            auth=self._auth,
        )
        if response.status_code not in {200, 201, 202, 204}:
            raise RuntimeError(f"Failed to replace named graph: {response.status_code}")

    def query_results(self, sparql: str, *, timeout: float, max_bytes: int) -> dict:
        with self._client.stream(
            "POST", self._endpoint("query"),
            data={"query": sparql, "timeout": str(int(timeout * 1000))},
            headers={"Accept": "application/sparql-results+json"},
            auth=self._auth, timeout=timeout,
        ) as response:
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > max_bytes:
                    raise ValueError("SPARQL result too large")
        payload = json.loads(body)
        if not isinstance(payload, dict) or not ("results" in payload or "boolean" in payload):
            raise ValueError("Invalid SPARQL JSON response")
        return payload

    def query(self, sparql: str) -> list[dict[str, object]]:
        response = self._client.post(
            self._endpoint("query"),
            data={"query": sparql},
            headers={"Accept": "application/sparql-results+json"},
            auth=self._auth,
        )
        if response.status_code not in {200, 201, 202, 204}:
            raise RuntimeError(f"SPARQL query failed: {response.status_code} {response.text}")
        if not response.content:
            return []

        payload = response.json()
        rows: list[dict[str, object]] = []
        for binding in payload.get("results", {}).get("bindings", []):
            row: dict[str, object] = {}
            for key, value in binding.items():
                row[key] = value.get("value")
            rows.append(row)
        return rows

