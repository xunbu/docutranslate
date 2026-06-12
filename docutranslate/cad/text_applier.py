# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
"""Apply translated text back to DXF files using ezdxf."""
from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_ENTITY_TYPES = ("TEXT", "MTEXT", "ATTDEF", "ATTRIB")


@dataclass
class ApplyResult:
    success: bool
    translated_count: int = 0
    message: str = ""


class CadTextApplier:
    """Apply translations back to DXF files."""

    def apply(
        self,
        dxf_path: str,
        output_path: str,
        translation_map: dict[str, str],
        mode: str = "replace",
        font_name: str = "Times New Roman",
        font_size_reduction: int = 2,
    ) -> ApplyResult:
        try:
            import ezdxf
        except ImportError:
            return ApplyResult(
                False, message="ezdxf not installed. Install with: pip install docutranslate[cad]"
            )

        src = Path(dxf_path)
        out = Path(output_path)
        if not src.exists():
            return ApplyResult(False, message=f"File not found: {dxf_path}")

        try:
            doc = ezdxf.readfile(str(src))
        except Exception as e:
            return ApplyResult(False, message=f"Cannot read DXF: {e}")

        replace_mode = mode == "replace"
        translated_count = 0

        def _process_space(space):
            nonlocal translated_count
            for entity in list(space):
                try:
                    if self._translate_entity(space, entity, translation_map, font_name, replace_mode, font_size_reduction, doc):
                        translated_count += 1
                except Exception as e:
                    logger.debug("Entity translate failed: %s", e)

        _process_space(doc.modelspace())
        for layout in doc.layouts:
            if layout.name != "Model":
                _process_space(layout)
        try:
            for block in doc.blocks:
                if not block.name.startswith("*"):
                    _process_space(block)
        except Exception as e:
            logger.debug("Block translate failed: %s", e)

        out.parent.mkdir(parents=True, exist_ok=True)
        doc.saveas(str(out))
        logger.info("Applied %d translations to %s", translated_count, out.name)
        return ApplyResult(True, translated_count, f"Translated {translated_count} entities")

    def _smart_match(self, text: str, translation_map: dict[str, str]) -> str | None:
        if text in translation_map and translation_map[text].strip():
            return translation_map[text]
        strategies = [
            lambda x: re.sub(r"\s+", "", x),
            lambda x: re.sub(r"\s+", " ", x.strip()),
            lambda x: x.strip(),
        ]
        for strategy in strategies:
            src = strategy(text)
            for orig, trans in translation_map.items():
                if strategy(orig) == src and trans.strip():
                    return trans
        return None

    def _set_font(self, entity, font_name: str, doc) -> None:
        try:
            style_name = f"TStyle_{font_name.replace(' ', '_')}"
            if style_name not in doc.styles:
                style = doc.styles.add(style_name, font=font_name)
                style.dxf.bigfont = ""
            entity.dxf.style = style_name
        except Exception as e:
            logger.debug("Set font failed: %s", e)

    def _translate_entity(self, owner, entity, translation_map, font_name, replace_mode, font_size_reduction, doc) -> bool:
        entity_type = entity.dxftype()
        if entity_type not in SUPPORTED_ENTITY_TYPES:
            return False

        try:
            if entity_type in ("TEXT", "MTEXT"):
                original_text = entity.dxf.text
            else:
                original_text = getattr(entity.dxf, "text", None) or getattr(entity.dxf, "tag", None)

            if not original_text or not original_text.strip():
                return False

            translated = self._smart_match(original_text.strip(), translation_map)
            if not translated:
                return False

            height = float(getattr(entity.dxf, "height", None) or getattr(entity.dxf, "char_height", 2.5))

            if replace_mode:
                if entity_type in ("TEXT", "ATTDEF", "ATTRIB"):
                    entity.dxf.text = translated
                    entity.dxf.height = max(1.0, height - font_size_reduction)
                elif entity_type == "MTEXT":
                    entity.dxf.text = translated
                    entity.dxf.char_height = max(1.0, height - font_size_reduction)
                self._set_font(entity, font_name, doc)
            else:
                self._add_text_below(owner, entity, translated, font_name, height, font_size_reduction, doc)

            return True
        except Exception as e:
            logger.debug("Translate entity failed: %s", e)
            return False

    def _add_text_below(self, owner, original_entity, translated_text, font_name, original_height, font_size_reduction, doc):
        try:
            insert_point = getattr(original_entity.dxf, "insert", (0, 0, 0))
            layer = getattr(original_entity.dxf, "layer", "0")
            rotation = float(getattr(original_entity.dxf, "rotation", 0))

            offset_y = -original_height * 1.2
            rotation_rad = rotation * (math.pi / 180.0)
            dx = offset_y * math.sin(rotation_rad)
            dy = offset_y * math.cos(rotation_rad)

            new_x = float(insert_point[0]) + dx
            new_y = float(insert_point[1]) + dy
            new_z = float(insert_point[2]) if len(insert_point) > 2 else 0.0

            style_name = f"TStyle_{font_name.replace(' ', '_')}"
            if style_name not in doc.styles:
                s = doc.styles.add(style_name, font=font_name)
                s.dxf.bigfont = ""

            attribs = {
                "insert": (new_x, new_y, new_z),
                "height": max(1.0, original_height - font_size_reduction),
                "layer": layer,
                "rotation": rotation,
                "color": 1,
                "style": style_name,
            }
            owner.add_text(translated_text, dxfattribs=attribs)
        except Exception as e:
            logger.debug("Add text below failed: %s", e)
