"""Temporal knowledge graph for agent memory (Graphiti-style)."""

import logging

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MemoryEntry(BaseModel):
    """Represents a memory entry in the temporal knowledge graph."""

    id: str
    agent_id: str
    simulation_id: str
    round_number: int
    content: str
    memory_type: str  # "observation", "reflection", "decision", "interaction"
    importance: float = 0.5  # 0.0-1.0
    timestamp: str
    related_entities: list[str] = []


class MemoryManager:
    """Temporal knowledge graph for agent memory using Neo4j."""

    def __init__(self, neo4j_client):
        self.db = neo4j_client

    async def add_memory(self, entry: MemoryEntry) -> str:
        """Store a memory entry in the temporal graph."""
        # Create memory node linked to agent and simulation
        query = """
        MATCH (agent:Agent {id: $agent_id})
        MATCH (sim:Simulation {id: $simulation_id})
        CREATE (m:Memory {
            id: $memory_id,
            content: $content,
            memory_type: $memory_type,
            importance: $importance,
            timestamp: $timestamp,
            round_number: $round_number,
            related_entities: $related_entities
        })
        CREATE (agent)-[:HAS_MEMORY]->(m)
        CREATE (m)-[:IN_SIMULATION]->(sim)
        RETURN m.id as memory_id
        """

        # If agent/simulation nodes don't exist, create them
        create_agent_query = """
        MERGE (agent:Agent {id: $agent_id})
        RETURN agent
        """
        create_sim_query = """
        MERGE (sim:Simulation {id: $simulation_id})
        RETURN sim
        """

        try:
            # Ensure agent and simulation nodes exist
            await self.db.execute_query(
                create_agent_query, {"agent_id": entry.agent_id}
            )
            await self.db.execute_query(
                create_sim_query, {"simulation_id": entry.simulation_id}
            )

            # Create memory node
            await self.db.execute_query(
                query,
                {
                    "memory_id": entry.id,
                    "agent_id": entry.agent_id,
                    "simulation_id": entry.simulation_id,
                    "content": entry.content,
                    "memory_type": entry.memory_type,
                    "importance": entry.importance,
                    "timestamp": entry.timestamp,
                    "round_number": entry.round_number,
                    "related_entities": entry.related_entities,
                },
            )

            logger.info(f"Added memory {entry.id} for agent {entry.agent_id}")
            return entry.id

        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            raise

    async def get_memories(
        self,
        agent_id: str,
        simulation_id: str,
        memory_type: str = None,
        limit: int = 20,
        min_importance: float = 0.0,
    ) -> list[MemoryEntry]:
        """Retrieve agent memories, optionally filtered."""
        if memory_type:
            query = """
            MATCH (agent:Agent {id: $agent_id})-[:HAS_MEMORY]->(m:Memory)
            MATCH (m)-[:IN_SIMULATION]->(sim:Simulation {id: $simulation_id})
            WHERE m.memory_type = $memory_type
              AND m.importance >= $min_importance
            RETURN m
            ORDER BY m.round_number DESC, m.timestamp DESC
            LIMIT $limit
            """
            params = {
                "agent_id": agent_id,
                "simulation_id": simulation_id,
                "memory_type": memory_type,
                "min_importance": min_importance,
                "limit": limit,
            }
        else:
            query = """
            MATCH (agent:Agent {id: $agent_id})-[:HAS_MEMORY]->(m:Memory)
            MATCH (m)-[:IN_SIMULATION]->(sim:Simulation {id: $simulation_id})
            WHERE m.importance >= $min_importance
            RETURN m
            ORDER BY m.round_number DESC, m.timestamp DESC
            LIMIT $limit
            """
            params = {
                "agent_id": agent_id,
                "simulation_id": simulation_id,
                "min_importance": min_importance,
                "limit": limit,
            }

        try:
            results = await self.db.execute_query(query, params)
            memories = []
            for record in results:
                node = record["m"]
                memories.append(
                    MemoryEntry(
                        id=node.get("id"),
                        agent_id=agent_id,
                        simulation_id=simulation_id,
                        round_number=node.get("round_number", 0),
                        content=node.get("content", ""),
                        memory_type=node.get("memory_type", "observation"),
                        importance=node.get("importance", 0.5),
                        timestamp=node.get("timestamp", ""),
                        related_entities=node.get("related_entities", []),
                    )
                )
            return memories
        except Exception as e:
            logger.error(f"Failed to get memories: {e}")
            return []

    async def get_recent_memories(
        self, agent_id: str, simulation_id: str, rounds: int = 3
    ) -> list[MemoryEntry]:
        """Get memories from the last N rounds."""
        # First get the current round number
        query = """
        MATCH (agent:Agent {id: $agent_id})-[:HAS_MEMORY]->(m:Memory)
        MATCH (m)-[:IN_SIMULATION]->(sim:Simulation {id: $simulation_id})
        RETURN max(m.round_number) as max_round
        """

        try:
            result = await self.db.execute_query(
                query, {"agent_id": agent_id, "simulation_id": simulation_id}
            )
            max_round = result[0].get("max_round", 0) if result else 0

            min_round = max(0, max_round - rounds + 1)

            query = """
            MATCH (agent:Agent {id: $agent_id})-[:HAS_MEMORY]->(m:Memory)
            MATCH (m)-[:IN_SIMULATION]->(sim:Simulation {id: $simulation_id})
            WHERE m.round_number >= $min_round
            RETURN m
            ORDER BY m.round_number DESC, m.timestamp DESC
            """

            results = await self.db.execute_query(
                query,
                {
                    "agent_id": agent_id,
                    "simulation_id": simulation_id,
                    "min_round": min_round,
                },
            )

            memories = []
            for record in results:
                node = record["m"]
                memories.append(
                    MemoryEntry(
                        id=node.get("id"),
                        agent_id=agent_id,
                        simulation_id=simulation_id,
                        round_number=node.get("round_number", 0),
                        content=node.get("content", ""),
                        memory_type=node.get("memory_type", "observation"),
                        importance=node.get("importance", 0.5),
                        timestamp=node.get("timestamp", ""),
                        related_entities=node.get("related_entities", []),
                    )
                )
            return memories
        except Exception as e:
            logger.error(f"Failed to get recent memories: {e}")
            return []

    async def search_memories(
        self, agent_id: str, simulation_id: str, query: str
    ) -> list[MemoryEntry]:
        """Search memories by content relevance."""
        # Simple keyword matching; can be enhanced with embeddings later
        keywords = query.lower().split()

        query_cypher = """
        MATCH (agent:Agent {id: $agent_id})-[:HAS_MEMORY]->(m:Memory)
        MATCH (m)-[:IN_SIMULATION]->(sim:Simulation {id: $simulation_id})
        WHERE ANY(keyword IN $keywords WHERE 
                  toLower(m.content) CONTAINS keyword)
        RETURN m
        ORDER BY m.importance DESC, m.round_number DESC
        LIMIT 20
        """

        try:
            results = await self.db.execute_query(
                query_cypher,
                {
                    "agent_id": agent_id,
                    "simulation_id": simulation_id,
                    "keywords": keywords,
                },
            )

            memories = []
            for record in results:
                node = record["m"]
                memories.append(
                    MemoryEntry(
                        id=node.get("id"),
                        agent_id=agent_id,
                        simulation_id=simulation_id,
                        round_number=node.get("round_number", 0),
                        content=node.get("content", ""),
                        memory_type=node.get("memory_type", "observation"),
                        importance=node.get("importance", 0.5),
                        timestamp=node.get("timestamp", ""),
                        related_entities=node.get("related_entities", []),
                    )
                )
            return memories
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []

    async def update_importance(self, memory_id: str, importance: float):
        """Update the importance score of a memory."""
        query = """
        MATCH (m:Memory {id: $memory_id})
        SET m.importance = $importance
        RETURN m
        """

        try:
            await self.db.execute_query(
                query, {"memory_id": memory_id, "importance": importance}
            )
            logger.info(f"Updated importance for memory {memory_id}")
        except Exception as e:
            logger.error(f"Failed to update memory importance: {e}")
            raise

    async def get_shared_memories(
        self, agent_ids: list[str], simulation_id: str
    ) -> list[MemoryEntry]:
        """Get memories shared/visible to multiple agents."""
        # Find memories that are linked to multiple agents
        # This could be through shared observations or interactions
        query = """
        MATCH (m:Memory)-[:IN_SIMULATION]->(
            sim:Simulation {id: $simulation_id}
        )
        WHERE m.memory_type IN ['interaction', 'observation']
        WITH m
        MATCH (agent)-[:HAS_MEMORY]->(m)
        WHERE agent.id IN $agent_ids
        WITH m, count(DISTINCT agent) as agent_count
        WHERE agent_count > 1
        RETURN m
        ORDER BY m.round_number DESC, m.timestamp DESC
        LIMIT 20
        """

        try:
            results = await self.db.execute_query(
                query, {"agent_ids": agent_ids, "simulation_id": simulation_id}
            )

            memories = []
            for record in results:
                node = record["m"]
                # Get the agent_id from the first linked agent
                agent_query = """
                MATCH (agent:Agent)-[:HAS_MEMORY]->(m:Memory {id: $memory_id})
                RETURN agent.id as agent_id
                LIMIT 1
                """
                agent_result = await self.db.execute_query(
                    agent_query, {"memory_id": node.get("id")}
                )
                agent_id = (
                    agent_result[0].get("agent_id", "unknown")
                    if agent_result
                    else "unknown"
                )

                memories.append(
                    MemoryEntry(
                        id=node.get("id"),
                        agent_id=agent_id,
                        simulation_id=simulation_id,
                        round_number=node.get("round_number", 0),
                        content=node.get("content", ""),
                        memory_type=node.get("memory_type", "observation"),
                        importance=node.get("importance", 0.5),
                        timestamp=node.get("timestamp", ""),
                        related_entities=node.get("related_entities", []),
                    )
                )
            return memories
        except Exception as e:
            logger.error(f"Failed to get shared memories: {e}")
            return []
