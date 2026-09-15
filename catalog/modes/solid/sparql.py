"""Bounded, read-only access to the materialized dataset. No remote federation."""

import json
import os
import re
import threading

import httpx
from fastapi import APIRouter, HTTPException, Request
from pyparsing import ParseResults
from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.parserutils import CompValue
from starlette.concurrency import run_in_threadpool


def _nodes(value):
    if isinstance(value, CompValue):
        yield value
        for child in value.values():
            yield from _nodes(child)
    elif isinstance(value, (list, tuple, ParseResults)):
        for child in value:
            yield from _nodes(child)


# Skip comments and IRIs while locating the already-validated query form.
_START = re.compile(r"#[^\r\n]*|<[^>]*>|\b(?:SELECT|ASK)\b", re.IGNORECASE)


def prepare_query(query: str, max_rows: int) -> str:
    # Unicode escapes can hide keywords from text-level rewriting. Literal Unicode
    # characters remain supported. Reject this uncommon spelling explicitly.
    if re.search(r"\\[uU][0-9a-fA-F]{4}", query):
        raise HTTPException(400, "Use literal Unicode characters instead of escapes")
    try:
        parsed = parseQuery(query)
        if parsed[1].name not in {"SelectQuery", "AskQuery"}:
            raise HTTPException(400, "Only SELECT and ASK queries are supported")
        for node in _nodes(parsed):
            if node.name in {"ServiceGraphPattern", "DatasetClause", "Function"}:
                raise HTTPException(400, "SERVICE, FROM and extension functions are disabled")
        # Also validate prefix resolution and expression semantics locally.
        translateQuery(parsed)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, "Invalid SPARQL SELECT/ASK query") from exc
    if parsed[1].name == "AskQuery":
        return query
    start = next(m for m in _START.finditer(query) if m.group().upper() == "SELECT")
    # A subselect preserves DISTINCT, aggregates, LIMIT, OFFSET, and projections.
    # A server-side outer limit bounds the number of rows even without user LIMIT.
    return (query[:start.start()] + "SELECT * WHERE { {\n" + query[start.start():]
            + f"\n}} }} LIMIT {max_rows}")


def sparql_routes(store) -> APIRouter:
    router = APIRouter()
    max_body = int(os.getenv("SPARQL_MAX_REQUEST_BYTES", "32768"))
    max_rows = int(os.getenv("SPARQL_MAX_ROWS", "500"))
    max_response = int(os.getenv("SPARQL_MAX_RESPONSE_BYTES", "2097152"))
    timeout = float(os.getenv("SPARQL_TIMEOUT_SECONDS", "10"))
    slots = threading.BoundedSemaphore(2)

    def execute(query):
        try:
            prepared = prepare_query(query, max_rows)
            return store.fuseki.query_results(
                prepared, timeout=timeout, max_bytes=max_response
            )
        finally:
            slots.release()

    @router.post("/sparql")
    async def sparql(request: Request):
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > max_body:
                raise HTTPException(413, "SPARQL request is too large")
        try:
            payload = json.loads(body)
            query = payload.get("query") if isinstance(payload, dict) else None
            if not isinstance(query, str) or not query.strip():
                raise ValueError()
        except (ValueError, UnicodeError) as exc:
            raise HTTPException(400, 'Expected JSON with a non-empty "query" string') from exc
        if not slots.acquire(blocking=False):
            raise HTTPException(429, "Query capacity reached; retry shortly")
        try:
            return await run_in_threadpool(execute, query)
        except httpx.TimeoutException as exc:
            raise HTTPException(504, "SPARQL query timed out") from exc
        except httpx.HTTPStatusError as exc:
            status = 400 if exc.response.status_code == 400 else 502
            raise HTTPException(status, "SPARQL query failed at the index") from exc
        except (httpx.RequestError, ValueError, RuntimeError) as exc:
            raise HTTPException(502, "Index unavailable or query result exceeds response limit") from exc

    return router
