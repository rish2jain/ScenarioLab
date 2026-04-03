"""Graph Building Engine for MiroFish.

This module provides knowledge graph functionality including:
- Neo4j database client for graph operations
- Seed material processing for document ingestion
- LLM-based entity and relationship extraction
- GraphRAG for retrieval-augmented generation
- Temporal memory management for agent simulations
"""

from app.graph.entity_extractor import (
    Entity,
    EntityExtractor,
    ExtractionResult,
    Relationship,
)
from app.graph.graphrag import GraphRAG, GraphRAGResult
from app.graph.memory import MemoryEntry, MemoryManager
from app.graph.neo4j_client import Neo4jClient
from app.graph.seed_processor import SeedMaterial, SeedProcessor

__all__ = [
    # Neo4j client
    "Neo4jClient",
    # Seed processing
    "SeedMaterial",
    "SeedProcessor",
    # Entity extraction
    "Entity",
    "Relationship",
    "ExtractionResult",
    "EntityExtractor",
    # GraphRAG
    "GraphRAGResult",
    "GraphRAG",
    # Memory
    "MemoryEntry",
    "MemoryManager",
]
