"""Neo4j database client with connection pooling."""

from __future__ import annotations

import asyncio
import logging
import re

from neo4j import AsyncDriver, AsyncGraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

logger = logging.getLogger(__name__)

# Pattern for valid Cypher identifiers (labels, relationship types, property keys)
_CYPHER_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(value: str, kind: str = "identifier") -> str:
    """Validate a Cypher identifier to prevent injection.

    Labels, relationship types, and property keys cannot be parameterized
    in Cypher, so they must be validated before interpolation.
    """
    if not _CYPHER_IDENTIFIER_RE.match(value):
        raise ValueError(f"Invalid Cypher {kind}: {value!r}. " "Must match [A-Za-z_][A-Za-z0-9_]*")
    return value


# Set by :func:`register_application_neo4j_client` from ``main`` lifespan so graph
# code uses the same connected pool as startup — not a separate lazy singleton.
_application_neo4j_client: Neo4jClient | None = None
_application_neo4j_registered: bool = False


def register_application_neo4j_client(client: Neo4jClient | None) -> None:
    """Store the Neo4j client created at app startup (or None if unavailable)."""
    global _application_neo4j_client, _application_neo4j_registered
    _application_neo4j_client = client
    _application_neo4j_registered = True


def get_application_neo4j_client() -> Neo4jClient | None:
    """Return the app-lifecycle Neo4j client, if startup registered one."""
    return _application_neo4j_client


def is_application_neo4j_registered() -> bool:
    """True after :func:`register_application_neo4j_client` runs (e.g. lifespan)."""
    return _application_neo4j_registered


def unregister_application_neo4j_client() -> None:
    """Clear app-lifecycle Neo4j registration (e.g. between tests).

    Best-effort closes the registered client via :func:`asyncio.run` because
    :meth:`Neo4jClient.close` is async. If called while an event loop is already
    running, await :meth:`Neo4jClient.close` yourself first, then unregister.
    """
    global _application_neo4j_client, _application_neo4j_registered
    client = _application_neo4j_client
    if client is not None:
        try:
            asyncio.run(client.close())
        except Exception as e:
            logger.warning("Failed to close Neo4j client during unregister: %s", e)
    _application_neo4j_client = None
    _application_neo4j_registered = False


class Neo4jClient:
    """Neo4j database client with connection pooling."""

    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        self._driver: AsyncDriver | None = None

    @property
    def is_connected(self) -> bool:
        return self._driver is not None

    async def connect(self):
        """Initialize connection pool."""
        try:
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
            # Verify connectivity
            await self._driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")
        except ServiceUnavailable as e:
            logger.error(f"Failed to connect to Neo4j at {self.uri}: {e}")
            raise
        except Neo4jError as e:
            logger.error(f"Neo4j error during connection: {e}")
            raise

    async def close(self):
        """Close connection pool."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")

    async def execute_query(self, query: str, parameters: dict = None) -> list[dict]:
        """Execute a Cypher query and return results."""
        if not self._driver:
            raise RuntimeError("Neo4j client not connected. Call connect() first.")

        parameters = parameters or {}
        try:
            async with self._driver.session() as session:
                result = await session.run(query, parameters)
                records = await result.data()
                return records
        except Neo4jError as e:
            logger.error(f"Query error: {e}. Query: {query[:80]}...")
            raise

    async def create_node(self, label: str, properties: dict) -> dict:
        """Create a node with given label and properties."""
        _validate_identifier(label, "label")

        # Add id if not present
        if "id" not in properties:
            import uuid

            properties["id"] = str(uuid.uuid4())

        # Validate property keys and build placeholders
        for key in properties:
            _validate_identifier(key, "property key")
        props_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
        query = f"CREATE (n:{label} {{{props_str}}}) RETURN n"

        result = await self.execute_query(query, properties)
        if result:
            node = result[0]["n"]
            return dict(node)
        return {}

    async def create_relationship(self, from_id: str, to_id: str, rel_type: str, properties: dict = None) -> dict:
        """Create a relationship between two nodes."""
        _validate_identifier(rel_type, "relationship type")
        properties = properties or {}

        # Add id if not present
        if "id" not in properties:
            import uuid

            properties["id"] = str(uuid.uuid4())

        # Validate property keys and build placeholders
        for key in properties:
            _validate_identifier(key, "property key")
        props_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
        if props_str:
            props_str = f" {{{props_str}}}"

        query = f"""
        MATCH (a), (b)
        WHERE a.id = $from_id AND b.id = $to_id
        CREATE (a)-[r:{rel_type}{props_str}]->(b)
        RETURN r
        """

        params = {"from_id": from_id, "to_id": to_id, **properties}
        result = await self.execute_query(query, params)
        if result:
            rel = result[0]["r"]
            return dict(rel)
        return {}

    async def get_node(self, node_id: str) -> dict | None:
        """Get a node by ID."""
        query = "MATCH (n {id: $node_id}) RETURN n"
        result = await self.execute_query(query, {"node_id": node_id})
        if result:
            return dict(result[0]["n"])
        return None

    async def get_neighbors(self, node_id: str, rel_type: str = None, depth: int = 1) -> list[dict]:
        """Get neighboring nodes with optional relationship filter."""
        if rel_type:
            _validate_identifier(rel_type, "relationship type")
            rel_pattern = f"[:{rel_type}]"
        else:
            rel_pattern = ""

        # Validate depth range
        depth = max(1, min(depth, 10))

        # Build variable-length path pattern
        if depth == 1:
            path_pattern = f"-{rel_pattern}-"
        else:
            if not rel_type:
                path_pattern = f"-[*1..{depth}]-"
            else:
                path_pattern = f"-[:{rel_type}*1..{depth}]-"

        query = f"""
        MATCH (n {{id: $node_id}}){path_pattern}(neighbor)
        WHERE neighbor.id <> $node_id
        RETURN DISTINCT neighbor
        """

        result = await self.execute_query(query, {"node_id": node_id})
        return [dict(record["neighbor"]) for record in result]

    async def search_nodes(self, label: str = None, properties: dict = None, limit: int = 50) -> list[dict]:
        """Search nodes by label and/or properties."""
        conditions = []
        # Cap limit to prevent unbounded queries
        limit = max(1, min(limit, 500))
        params = {"limit": limit}

        if label:
            _validate_identifier(label, "label")
            match_clause = f"MATCH (n:{label})"
        else:
            match_clause = "MATCH (n)"

        if properties:
            for key, value in properties.items():
                _validate_identifier(key, "property key")
                param_key = f"prop_{key}"
                conditions.append(f"n.{key} = ${param_key}")
                params[param_key] = value

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        query = f"""
        {match_clause}
        {where_clause}
        RETURN n
        LIMIT $limit
        """

        result = await self.execute_query(query, params)
        return [dict(record["n"]) for record in result]

    async def get_subgraph(self, center_node_id: str, depth: int = 2) -> dict:
        """Get a subgraph around a center node.

        Returns:
            dict with keys: nodes, relationships
        """
        # Cypher does not support parameters in variable-length paths,
        # so depth must be interpolated as a validated integer literal.
        depth = max(1, min(int(depth), 10))
        query = f"""
        MATCH path = (center {{id: $center_id}})-[*1..{depth}]-(connected)
        WITH center, nodes(path) as path_nodes,
             relationships(path) as path_rels
        UNWIND path_nodes as node
        UNWIND path_rels as rel
        RETURN collect(DISTINCT node) as nodes,
               collect(DISTINCT rel) as relationships
        """

        result = await self.execute_query(query, {"center_id": center_node_id})

        if not result:
            return {"nodes": [], "relationships": []}

        nodes = [dict(n) for n in result[0]["nodes"]]
        relationships = [dict(r) for r in result[0]["relationships"]]

        return {"nodes": nodes, "relationships": relationships}

    async def clear_graph(self, seed_id: str = None):
        """Clear graph data, optionally scoped to a seed_id.

        All nodes written for entity extraction set ``seed_id`` on the node.
        Uses ``DETACH DELETE`` so relationships are removed with their endpoints.
        If the driver was idle long enough to drop, attempts a reconnect before
        deleting so cleanup is less likely to be skipped silently.
        """
        if seed_id:
            if not self._driver:
                logger.warning(
                    "clear_graph(%s): no Neo4j driver; attempting reconnect before cleanup",
                    seed_id,
                )
                await self.connect()
            try:
                await self._driver.verify_connectivity()
            except Exception:
                logger.warning(
                    "Neo4j connectivity check failed; reconnecting before clear_graph(%s)",
                    seed_id,
                )
                await self.close()
                await self.connect()
            query = """
            MATCH (n)
            WHERE n.seed_id = $seed_id
            DETACH DELETE n
            """
            await self.execute_query(query, {"seed_id": seed_id})
            logger.info(f"Cleared graph data for seed_id: {seed_id}")
        else:
            # Clear all graph data (use with caution)
            query = "MATCH (n) DETACH DELETE n"
            await self.execute_query(query)
            logger.info("Cleared all graph data")
