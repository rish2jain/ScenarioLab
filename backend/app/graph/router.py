"""FastAPI router for graph operations."""

import logging
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import settings
from app.graph.entity_extractor import EntityExtractor
from app.graph.graphrag import GraphRAG
from app.graph.neo4j_client import Neo4jClient
from app.graph.seed_processor import SeedProcessor
from app.llm.factory import get_llm_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["graph"])

# Global instances (initialized on first use)
_neo4j_client: Optional[Neo4jClient] = None
_seed_processor: Optional[SeedProcessor] = None
_entity_extractor: Optional[EntityExtractor] = None
_graphrag: Optional[GraphRAG] = None


def get_neo4j_client() -> Neo4jClient:
    """Get or create Neo4j client singleton."""
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
        )
    return _neo4j_client


def get_seed_processor() -> SeedProcessor:
    """Get or create seed processor singleton."""
    global _seed_processor
    if _seed_processor is None:
        _seed_processor = SeedProcessor()
    return _seed_processor


def get_entity_extractor() -> EntityExtractor:
    """Get or create entity extractor singleton."""
    global _entity_extractor
    if _entity_extractor is None:
        llm = get_llm_provider()
        _entity_extractor = EntityExtractor(llm)
    return _entity_extractor


def get_graphrag() -> GraphRAG:
    """Get or create GraphRAG singleton."""
    global _graphrag
    if _graphrag is None:
        neo4j = get_neo4j_client()
        llm = get_llm_provider()
        _graphrag = GraphRAG(neo4j, llm)
    return _graphrag


# Request/Response models


class SeedResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    status: str
    entity_count: int
    relationship_count: int
    error_message: Optional[str] = None


class SeedListResponse(BaseModel):
    seeds: list[SeedResponse]


class GraphQueryRequest(BaseModel):
    question: str
    seed_id: Optional[str] = None
    max_depth: int = 2


class GraphQueryResponse(BaseModel):
    query: str
    entities: list[dict]
    relationships: list[dict]
    context: str


class GraphDataResponse(BaseModel):
    nodes: list[dict]
    relationships: list[dict]


# Endpoints


@router.post("/seeds/upload", response_model=SeedResponse)
async def upload_seed_file(
    file: UploadFile = File(...),
):
    """Upload seed material file, process it, extract entities, build graph."""
    processor = get_seed_processor()
    neo4j = get_neo4j_client()
    extractor = get_entity_extractor()

    # Read file content
    content = await file.read()
    content_type = file.content_type or "text/plain"

    logger.info(f"Uploading file: {file.filename} ({content_type})")

    # Process file
    seed = await processor.process_file(file.filename, content, content_type)

    if seed.status == "failed":
        raise HTTPException(
            status_code=400,
            detail=f"Failed to process file: {seed.error_message}"
        )

    # Extract entities and build graph (if processing succeeded)
    if seed.status == "processed" and seed.processed_content:
        try:
            # Chunk content
            chunks = await processor.chunk_content(
                seed.processed_content, chunk_size=3000, overlap=300
            )

            # Extract entities from chunks
            extraction_result = await extractor.extract_from_chunks(chunks)

            # Store entities and relationships in Neo4j
            entity_id_map = {}

            # Create entity nodes
            for entity in extraction_result.entities:
                node_props = {
                    "id": entity.id,
                    "name": entity.name,
                    "entity_type": entity.entity_type,
                    "description": entity.description,
                    "seed_id": seed.id,
                    **entity.properties,
                }
                await neo4j.create_node("Entity", node_props)
                entity_id_map[entity.id] = entity.id

            # Create relationships
            for rel in extraction_result.relationships:
                rel_props = {
                    "id": rel.id,
                    "relationship_type": rel.relationship_type,
                    "description": rel.description,
                    "weight": rel.weight,
                    **rel.properties,
                }
                await neo4j.create_relationship(
                    from_id=rel.source_entity_id,
                    to_id=rel.target_entity_id,
                    rel_type=rel.relationship_type.upper(),
                    properties=rel_props,
                )

            # Update seed with counts
            seed.entity_count = len(extraction_result.entities)
            seed.relationship_count = len(extraction_result.relationships)

            logger.info(
                f"Built graph for seed {seed.id}: "
                f"{seed.entity_count} entities, "
                f"{seed.relationship_count} relationships"
            )

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            seed.status = "failed"
            seed.error_message = str(e)

    return SeedResponse(
        id=seed.id,
        filename=seed.filename,
        content_type=seed.content_type,
        status=seed.status,
        entity_count=seed.entity_count,
        relationship_count=seed.relationship_count,
        error_message=seed.error_message,
    )


@router.get("/seeds", response_model=SeedListResponse)
async def list_seeds():
    """List all uploaded seeds."""
    processor = get_seed_processor()
    seeds = await processor.list_seeds()

    return SeedListResponse(
        seeds=[
            SeedResponse(
                id=s.id,
                filename=s.filename,
                content_type=s.content_type,
                status=s.status,
                entity_count=s.entity_count,
                relationship_count=s.relationship_count,
                error_message=s.error_message,
            )
            for s in seeds
        ]
    )


@router.get("/seeds/{seed_id}", response_model=SeedResponse)
async def get_seed(seed_id: str):
    """Get seed material info and processing status."""
    processor = get_seed_processor()
    seed = await processor.get_seed(seed_id)

    if not seed:
        raise HTTPException(status_code=404, detail="Seed not found")

    return SeedResponse(
        id=seed.id,
        filename=seed.filename,
        content_type=seed.content_type,
        status=seed.status,
        entity_count=seed.entity_count,
        relationship_count=seed.relationship_count,
        error_message=seed.error_message,
    )


@router.get("/seeds/{seed_id}/graph", response_model=GraphDataResponse)
async def get_seed_graph(seed_id: str):
    """Get the knowledge graph for a seed (nodes + relationships)."""
    neo4j = get_neo4j_client()
    processor = get_seed_processor()

    # Verify seed exists
    seed = await processor.get_seed(seed_id)
    if not seed:
        raise HTTPException(status_code=404, detail="Seed not found")

    # Query Neo4j for entities with this seed_id
    entity_query = """
    MATCH (n {seed_id: $seed_id})
    RETURN n
    """
    entity_results = await neo4j.execute_query(
        entity_query, {"seed_id": seed_id}
    )
    nodes = [dict(r["n"]) for r in entity_results]

    # Get relationships between these nodes
    node_ids = [n.get("id") for n in nodes]
    if node_ids:
        rel_query = """
        MATCH (a)-[r]->(b)
        WHERE a.id IN $node_ids AND b.id IN $node_ids
        RETURN r, startNode(r) as start, endNode(r) as end
        """
        rel_results = await neo4j.execute_query(
            rel_query, {"node_ids": node_ids}
        )
        relationships = []
        for record in rel_results:
            rel = dict(record["r"])
            rel["source_entity_id"] = record["start"].get("id")
            rel["target_entity_id"] = record["end"].get("id")
            relationships.append(rel)
    else:
        relationships = []

    return GraphDataResponse(
        nodes=nodes,
        relationships=relationships,
    )


@router.post("/graph/query", response_model=GraphQueryResponse)
async def query_graph(request: GraphQueryRequest):
    """Query the graph with natural language (GraphRAG)."""
    graphrag = get_graphrag()

    try:
        result = await graphrag.query(
            question=request.question,
            seed_id=request.seed_id,
            max_depth=request.max_depth,
        )

        return GraphQueryResponse(
            query=result.query,
            entities=result.entities,
            relationships=result.relationships,
            context=result.context,
        )
    except Exception as e:
        logger.error(f"Graph query failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Query failed: {str(e)}"
        )
