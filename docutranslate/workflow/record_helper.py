# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


@dataclass(frozen=True)
class RecordFieldMapping:
    """Defines the field mapping for a record-based JSON structure.

    Default layout matches ``{"records": [{"record_id": "...", "source_text": "..."}]}``
    but every field name is configurable so that *any* structured data with
    an ID field and a text field can be translated without a custom adapter.
    """
    id_field: str = "record_id"
    text_field: str = "source_text"
    records_key: str = "records"


class RecordTranslationHelper:
    """Utility that bridges the "records with IDs" pattern and the existing
    ``JsonWorkflow`` / ``Client.translate`` pipeline.

    Usage::

        helper = RecordTranslationHelper()
        payload  = helper.build_payload(records)
        paths    = helper.build_json_paths()
        # ... feed payload + paths to JsonWorkflow / Client.translate ...
        results  = helper.extract_translated_records(records, translated_payload)
    """

    def __init__(self, field_mapping: RecordFieldMapping | None = None):
        self.field_mapping = field_mapping or RecordFieldMapping()

    # ------------------------------------------------------------------
    # Payload construction
    # ------------------------------------------------------------------

    def build_json_paths(self) -> list[str]:
        """Return the ``json_paths`` expression that targets *only* the text
        field inside each record."""
        fm = self.field_mapping
        return [f"$.{fm.records_key}[*].{fm.text_field}"]

    def build_payload(self, records: Sequence[Dict[str, Any]]) -> dict[str, Any]:
        """Wrap *records* inside the expected JSON envelope."""
        return {self.field_mapping.records_key: list(records)}

    # ------------------------------------------------------------------
    # Result extraction
    # ------------------------------------------------------------------

    def extract_translated_records(
        self,
        original_records: Sequence[Dict[str, Any]],
        translated_payload: Dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Map the translated payload back onto the original record order.

        * All non-text fields are preserved from the original record.
        * The text field is replaced with the translated value.
        * If a record ID is missing from the translated payload the original
          record is returned unchanged (graceful degradation).
        """
        fm = self.field_mapping
        translated_items: list[dict[str, Any]] = translated_payload.get(fm.records_key, [])

        # Index translated items by ID
        translated_by_id: dict[str, dict[str, Any]] = {}
        for item in translated_items:
            if not isinstance(item, dict):
                continue
            rid = str(item.get(fm.id_field, ""))
            if rid:
                translated_by_id[rid] = item

        results: list[dict[str, Any]] = []
        for original in original_records:
            rid = str(original.get(fm.id_field, ""))
            translated = translated_by_id.get(rid)
            if translated and isinstance(translated.get(fm.text_field), str):
                merged = dict(original)  # preserve all original fields
                merged[fm.text_field] = translated[fm.text_field]
                results.append(merged)
            else:
                results.append(dict(original))
        return results

    # ------------------------------------------------------------------
    # Convenience: file I/O for SDK / API integration
    # ------------------------------------------------------------------

    def write_payload_to_file(
        self,
        records: Sequence[Dict[str, Any]],
        output_path: Path | str,
    ) -> Path:
        """Serialize *records* as a JSON file suitable for ``JsonWorkflow``."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.build_payload(records)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def read_translated_payload(self, file_path: Path | str) -> dict[str, Any]:
        """Read a translated JSON file back into a dict."""
        return json.loads(Path(file_path).read_text(encoding="utf-8"))
