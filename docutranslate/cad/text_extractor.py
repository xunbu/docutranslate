# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
"""Extract text entities from DXF files using ezdxf."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SUPPORTED_ENTITY_TYPES = ("TEXT", "MTEXT", "ATTDEF", "ATTRIB")


@dataclass
class TextEntity:
    text: str
    entity_type: str
    layer: str
    insert_x: float = 0.0
    insert_y: float = 0.0
    insert_z: float = 0.0
    height: float = 2.5
    rotation: float = 0.0
    space: str = "ModelSpace"


@dataclass
class ExtractionResult:
    success: bool
    entities: list[TextEntity] = field(default_factory=list)
    message: str = ""


class CadTextExtractor:
    """Extract text entities from DXF files."""

    def extract(self, dxf_path: str) -> ExtractionResult:
        try:
            import ezdxf
        except ImportError:
            return ExtractionResult(
                False, message="ezdxf not installed. Install with: pip install docutranslate[cad]"
            )

        path = Path(dxf_path)
        if not path.exists():
            return ExtractionResult(False, message=f"File not found: {dxf_path}")

        try:
            doc = ezdxf.readfile(str(path))
        except Exception as e:
            return ExtractionResult(False, message=f"Cannot read DXF: {e}")

        entities: list[TextEntity] = []

        # Model space
        entities.extend(self._extract_space(doc.modelspace(), "ModelSpace"))

        # Paper space layouts
        for layout in doc.layouts:
            if layout.name != "Model":
                entities.extend(self._extract_space(layout, f"PaperSpace_{layout.name}"))

        # Block definitions
        try:
            for block in doc.blocks:
                if not block.name.startswith("*"):
                    entities.extend(self._extract_space(block, f"Block_{block.name}"))
        except Exception as e:
            logger.debug("Block extraction failed: %s", e)

        logger.info("Extracted %d text entities from %s", len(entities), path.name)
        return ExtractionResult(True, entities, f"Extracted {len(entities)} text entities")

    def _extract_space(self, space, space_name: str) -> list[TextEntity]:
        entities = []
        for entity in space:
            try:
                text_entity = self._extract_entity(entity, space_name)
                if text_entity:
                    entities.append(text_entity)
            except Exception as e:
                logger.debug("Entity extraction failed: %s", e)
        return entities

    def _extract_entity(self, entity, space_name: str) -> TextEntity | None:
        entity_type = entity.dxftype()
        if entity_type not in SUPPORTED_ENTITY_TYPES:
            return None

        try:
            if entity_type in ("TEXT", "MTEXT"):
                text_content = entity.dxf.text
            else:
                text_content = getattr(entity.dxf, "text", None) or getattr(entity.dxf, "tag", None)

            if not text_content or not text_content.strip():
                return None

            insert_point = getattr(entity.dxf, "insert", (0, 0, 0))
            height = getattr(entity.dxf, "height", None) or getattr(entity.dxf, "char_height", 2.5)
            layer = getattr(entity.dxf, "layer", "0")
            rotation = getattr(entity.dxf, "rotation", 0)

            return TextEntity(
                text=text_content.strip(),
                entity_type=entity_type,
                layer=layer,
                insert_x=float(insert_point[0]),
                insert_y=float(insert_point[1]),
                insert_z=float(insert_point[2]) if len(insert_point) > 2 else 0.0,
                height=float(height),
                rotation=float(rotation),
                space=space_name,
            )
        except Exception as e:
            logger.debug("Entity parse failed: %s", e)
            return None

    def to_translation_records(self, result: ExtractionResult) -> list[dict[str, Any]]:
        """Convert extraction result to records format for translation."""
        records = []
        for i, entity in enumerate(result.entities):
            records.append({
                "record_id": f"cad_{i}",
                "source_text": entity.text,
                "_entity_type": entity.entity_type,
                "_layer": entity.layer,
                "_space": entity.space,
            })
        return records
