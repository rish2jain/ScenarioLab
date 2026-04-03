"""Graph-based Retrieval-Augmented Generation."""

import logging

from pydantic import BaseModel

from app.llm.provider import LLMMessage

logger = logging.getLogger(__name__)


class GraphRAGResult(BaseModel):
    """Result of a GraphRAG query."""

    query: str
    entities: list[dict]
    relationships: list[dict]
    context: str  # Assembled context string for LLM consumption


class GraphRAG:
    """Graph-based Retrieval-Augmented Generation."""

    def __init__(self, neo4j_client, llm_provider):
        self.db = neo4j_client
        self.llm = llm_provider

    async def query(
        self, question: str, seed_id: str = None, max_depth: int = 2
    ) -> GraphRAGResult:
        """Query the knowledge graph with a natural language question."""
        # 1. Use LLM to extract key entities from the question
        key_entities = await self._extract_query_entities(question)
        logger.info(f"Extracted key entities from query: {key_entities}")

        # 2. Search Neo4j for matching nodes
        matched_nodes = []
        for entity_name in key_entities:
            # Search by name (case-insensitive contains)
            query = """
            MATCH (n)
            WHERE toLower(n.name) CONTAINS toLower($name)
            RETURN n
            LIMIT 5
            """
            results = await self.db.execute_query(query, {"name": entity_name})
            matched_nodes.extend([dict(r["n"]) for r in results])

        # Also search by description
        for entity_name in key_entities:
            query = """
            MATCH (n)
            WHERE toLower(n.description) CONTAINS toLower($name)
            RETURN n
            LIMIT 3
            """
            results = await self.db.execute_query(query, {"name": entity_name})
            matched_nodes.extend([dict(r["n"]) for r in results])

        # Deduplicate nodes
        seen_ids = set()
        unique_nodes = []
        for node in matched_nodes:
            if node.get("id") not in seen_ids:
                seen_ids.add(node.get("id"))
                unique_nodes.append(node)

        logger.info(f"Found {len(unique_nodes)} matching nodes")

        # 3. Expand to neighboring nodes (up to max_depth)
        all_nodes = {n.get("id"): n for n in unique_nodes}
        all_relationships = []

        for node in unique_nodes:
            subgraph = await self.db.get_subgraph(
                node.get("id"), depth=max_depth
            )
            for n in subgraph.get("nodes", []):
                if n.get("id") not in all_nodes:
                    all_nodes[n.get("id")] = n
            all_relationships.extend(subgraph.get("relationships", []))

        # Deduplicate relationships
        seen_rels = set()
        unique_relationships = []
        for rel in all_relationships:
            rel_key = (
                rel.get("source_entity_id", rel.get("start")),
                rel.get("target_entity_id", rel.get("end")),
                rel.get("relationship_type", rel.get("type")),
            )
            if rel_key not in seen_rels:
                seen_rels.add(rel_key)
                unique_relationships.append(rel)

        logger.info(
            f"Expanded to {len(all_nodes)} nodes and "
            f"{len(unique_relationships)} relationships"
        )

        # 4. Assemble context from retrieved subgraph
        context = self._assemble_context(
            list(all_nodes.values()), unique_relationships
        )

        return GraphRAGResult(
            query=question,
            entities=list(all_nodes.values()),
            relationships=unique_relationships,
            context=context,
        )

    async def _extract_query_entities(self, question: str) -> list[str]:
        """Extract key entities from a natural language query."""
        prompt = f"""Extract key entity names from this question.
Return a JSON array of entity names (organizations, people, products, 
locations, etc.) that are explicitly mentioned or strongly implied.

Question: {question}

Respond with valid JSON array only, e.g.: ["Entity1", "Entity2"]
"""

        messages = [
            LLMMessage(
                role="system",
                content="You extract entity names from questions. "
                        "Return only a JSON array."
            ),
            LLMMessage(role="user", content=prompt),
        ]

        try:
            response = await self.llm.generate(
                messages=messages, temperature=0.3, max_tokens=500
            )

            content = response.content.strip()

            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            content = content.strip()

            import json

            entities = json.loads(content)
            if isinstance(entities, list):
                return [e for e in entities if isinstance(e, str)]
            return []
        except Exception as e:
            logger.error(f"Failed to extract query entities: {e}")
            # Fallback: return empty list
            return []

    def _assemble_context(
        self, nodes: list[dict], relationships: list[dict]
    ) -> str:
        """Assemble context string from nodes and relationships."""
        context_parts = []

        # Add nodes section
        if nodes:
            context_parts.append("## Entities\n")
            for node in nodes:
                name = node.get("name", "Unknown")
                entity_type = node.get("entity_type", "unknown")
                description = node.get("description", "")
                context_parts.append(
                    f"- **{name}** ({entity_type}): {description}"
                )

        # Add relationships section
        if relationships:
            context_parts.append("\n## Relationships\n")

            # Build a lookup for node names
            node_names = {n.get("id"): n.get("name", "Unknown") for n in nodes}

            for rel in relationships:
                rel_type = rel.get(
                    "relationship_type", rel.get("type", "related_to")
                )
                source_id = rel.get("source_entity_id") or rel.get(
                    "start_node_id"
                ) or rel.get("start")
                target_id = rel.get("target_entity_id") or rel.get(
                    "end_node_id"
                ) or rel.get("end")
                source_name = node_names.get(source_id, "Unknown")
                target_name = node_names.get(target_id, "Unknown")
                description = rel.get("description", "")
                weight = rel.get("weight", 1.0)

                context_parts.append(
                    f"- {source_name} **{rel_type}** {target_name} "
                    f"(weight: {weight:.2f}): {description}"
                )

        return "\n".join(context_parts)

    async def get_context_for_agent(
        self, agent_role: str, seed_id: str, topics: list[str] = None
    ) -> str:
        """Get relevant context from the knowledge graph for an agent."""
        # Query graph for entities relevant to the agent's role
        relevant_nodes = []

        # Search by role keywords
        role_keywords = agent_role.lower().split()
        for keyword in role_keywords:
            query = """
            MATCH (n)
            WHERE toLower(n.name) CONTAINS $keyword
               OR toLower(n.description) CONTAINS $keyword
            RETURN n
            LIMIT 10
            """
            results = await self.db.execute_query(query, {"keyword": keyword})
            relevant_nodes.extend([dict(r["n"]) for r in results])

        # Search by topics if provided
        if topics:
            for topic in topics:
                query = """
                MATCH (n)
                WHERE toLower(n.name) CONTAINS $topic
                   OR toLower(n.description) CONTAINS $topic
                RETURN n
                LIMIT 10
                """
                results = await self.db.execute_query(
                    query, {"topic": topic.lower()}
                )
                relevant_nodes.extend([dict(r["n"]) for r in results])

        # Deduplicate
        seen_ids = set()
        unique_nodes = []
        for node in relevant_nodes:
            if node.get("id") not in seen_ids:
                seen_ids.add(node.get("id"))
                unique_nodes.append(node)

        # Get relationships between relevant nodes
        node_ids = [n.get("id") for n in unique_nodes]
        relationships = []

        if len(node_ids) > 1:
            # Find relationships between the relevant nodes
            query = """
            MATCH (a)-[r]->(b)
            WHERE a.id IN $node_ids AND b.id IN $node_ids
            RETURN r
            LIMIT 50
            """
            params = {"node_ids": node_ids}
            results = await self.db.execute_query(query, params)
            relationships = [dict(r["r"]) for r in results]

        # Assemble context
        context = self._assemble_context(unique_nodes, relationships)

        # Add agent-specific framing
        header = f"""# Knowledge Graph Context for {agent_role}

This context provides relevant entities and relationships from the 
knowledge graph that may inform your decisions and responses.

"""

        return header + context
