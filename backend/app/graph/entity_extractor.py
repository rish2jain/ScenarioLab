"""LLM-based entity and relationship extraction."""

import json
import logging
import uuid
from difflib import SequenceMatcher

from pydantic import BaseModel, Field

from app.llm.provider import LLMMessage

logger = logging.getLogger(__name__)


class Entity(BaseModel):
    """Represents an extracted entity."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    entity_type: str  # "organization", "person", "policy",
    # "financial_figure", "timeline", "dependency", "location", "event"
    description: str
    properties: dict = {}


class Relationship(BaseModel):
    """Represents a relationship between entities."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    # "works_for", "competes_with", "regulates", "depends_on",
    # "leads", "reports_to", etc.
    description: str
    weight: float = 1.0
    properties: dict = {}


class ExtractionResult(BaseModel):
    """Result of entity and relationship extraction."""

    entities: list[Entity]
    relationships: list[Relationship]


class EntityExtractor:
    """Uses LLM to extract entities and relationships from text."""

    ENTITY_TYPES = [
        "organization",
        "person",
        "policy",
        "financial_figure",
        "timeline",
        "dependency",
        "location",
        "event",
    ]

    RELATIONSHIP_TYPES = [
        "works_for",
        "competes_with",
        "regulates",
        "depends_on",
        "leads",
        "reports_to",
        "owns",
        "invests_in",
        "partners_with",
        "acquired",
        "influences",
        "located_in",
        "occurred_at",
        "related_to",
    ]

    def __init__(self, llm_provider):
        self.llm = llm_provider

    def _build_extraction_prompt(self, text: str) -> str:
        """Build the prompt for entity and relationship extraction."""
        entity_types_str = ", ".join(self.ENTITY_TYPES)
        rel_types_str = ", ".join(self.RELATIONSHIP_TYPES)

        prompt = f"""You are an expert information extraction system for 
strategy consulting analysis.

Extract entities and relationships from the following text. Focus on 
entities relevant to business strategy, competitive analysis, and 
organizational dynamics.

Entity Types to extract: {entity_types_str}

Relationship Types to extract: {rel_types_str}

For each entity, provide:
- name: The entity name
- entity_type: One of the types listed above
- description: A brief description (1-2 sentences)
- properties: Any additional relevant attributes as key-value pairs

For each relationship, provide:
- source_entity_name: Name of the source entity
- target_entity_name: Name of the target entity  
- relationship_type: One of the types listed above
- description: Brief description of the relationship
- weight: Importance score from 0.0 to 1.0

Text to analyze:
---
{text[:8000]}  # Limit text to avoid token limits
---

Respond with valid JSON in this exact format:
{{
  "entities": [
    {{
      "name": "Entity Name",
      "entity_type": "organization",
      "description": "Description here",
      "properties": {{}}
    }}
  ],
  "relationships": [
    {{
      "source_entity_name": "Source Name",
      "target_entity_name": "Target Name",
      "relationship_type": "works_for",
      "description": "Description here",
      "weight": 0.8
    }}
  ]
}}

Extract as many meaningful entities and relationships as possible. 
Ensure all relationship source/target names match extracted entity names.
"""
        return prompt

    async def extract_from_text(self, text: str) -> ExtractionResult:
        """Extract entities and relationships from a text chunk."""
        prompt = self._build_extraction_prompt(text)

        messages = [
            LLMMessage(role="system", content="You are a precise "
                       "information extraction system."),
            LLMMessage(role="user", content=prompt),
        ]

        try:
            response = await self.llm.generate(
                messages=messages,
                temperature=0.3,
                max_tokens=4096,
            )

            # Parse the JSON response
            content = response.content.strip()

            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            content = content.strip()

            data = json.loads(content)

            # Create entities
            entities = []
            name_to_entity = {}
            for entity_data in data.get("entities", []):
                entity = Entity(
                    name=entity_data["name"],
                    entity_type=entity_data["entity_type"],
                    description=entity_data.get("description", ""),
                    properties=entity_data.get("properties", {}),
                )
                entities.append(entity)
                name_to_entity[entity.name.lower()] = entity

            # Create relationships
            relationships = []
            for rel_data in data.get("relationships", []):
                source_name = rel_data["source_entity_name"].lower()
                target_name = rel_data["target_entity_name"].lower()

                # Find matching entities
                source_entity = name_to_entity.get(source_name)
                target_entity = name_to_entity.get(target_name)

                if source_entity and target_entity:
                    relationship = Relationship(
                        source_entity_id=source_entity.id,
                        target_entity_id=target_entity.id,
                        relationship_type=rel_data["relationship_type"],
                        description=rel_data.get("description", ""),
                        weight=rel_data.get("weight", 1.0),
                        properties=rel_data.get("properties", {}),
                    )
                    relationships.append(relationship)
                else:
                    logger.warning(
                        f"Skipping relationship: entity not found "
                        f"({rel_data.get('source_entity_name')} -> "
                        f"{rel_data.get('target_entity_name')})"
                    )

            logger.info(
                f"Extracted {len(entities)} entities and "
                f"{len(relationships)} relationships"
            )

            return ExtractionResult(
                entities=entities, relationships=relationships
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response content: {response.content[:500]}...")
            return ExtractionResult(entities=[], relationships=[])
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            return ExtractionResult(entities=[], relationships=[])

    async def extract_from_chunks(
        self, chunks: list[str]
    ) -> ExtractionResult:
        """Extract from multiple chunks and merge/deduplicate."""
        results = []

        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i + 1}/{len(chunks)}")
            result = await self.extract_from_text(chunk)
            results.append(result)

        return await self.merge_results(results)

    def _similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity."""
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    async def merge_results(
        self, results: list[ExtractionResult]
    ) -> ExtractionResult:
        """Merge multiple extraction results, deduplicating entities."""
        merged_entities: list[Entity] = []
        merged_relationships: list[Relationship] = []

        # Track entity IDs for relationship mapping
        name_to_merged_entity: dict[str, Entity] = {}

        # Similarity threshold for deduplication
        SIMILARITY_THRESHOLD = 0.85

        for result in results:
            # Merge entities
            for entity in result.entities:
                # Check for duplicates
                is_duplicate = False
                for existing in merged_entities:
                    if (
                        entity.entity_type == existing.entity_type
                        and self._similarity(
                            entity.name, existing.name
                        ) > SIMILARITY_THRESHOLD
                    ):
                        is_duplicate = True
                        name_to_merged_entity[entity.name.lower()] = existing
                        break

                if not is_duplicate:
                    merged_entities.append(entity)
                    name_to_merged_entity[entity.name.lower()] = entity

            # Merge relationships
            for rel in result.relationships:
                # Skip if source or target not in merged entities
                source_found = False
                target_found = False

                for entity in merged_entities:
                    if entity.id == rel.source_entity_id:
                        source_found = True
                    if entity.id == rel.target_entity_id:
                        target_found = True

                if source_found and target_found:
                    # Check for duplicate relationships
                    is_duplicate = False
                    for existing in merged_relationships:
                        if (
                            rel.source_entity_id == existing.source_entity_id
                            and rel.target_entity_id
                            == existing.target_entity_id
                            and rel.relationship_type
                            == existing.relationship_type
                        ):
                            is_duplicate = True
                            break

                    if not is_duplicate:
                        merged_relationships.append(rel)

        logger.info(
            f"Merged results: {len(merged_entities)} entities, "
            f"{len(merged_relationships)} relationships"
        )

        return ExtractionResult(
            entities=merged_entities, relationships=merged_relationships
        )
