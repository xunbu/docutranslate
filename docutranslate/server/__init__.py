# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
"""
DocuTranslate Shared Server Layer

This module provides a shared TranslationService that is used by both
the Web backend (app.py) and MCP server to ensure consistent task management.

Example:
    from docutranslate.server import TranslationService, get_translation_service

    # Get the singleton instance
    service = get_translation_service()

    # Start a translation
    result = await service.start_translation(task_id, payload, file_bytes, filename)

    # Get task status
    state = service.get_task_state(task_id)
"""

from docutranslate.server.core import (
    TranslationService,
    get_translation_service,
    QueueAndHistoryHandler,
    get_workflow_type_from_filename,
    WORKFLOW_DICT,
    MEDIA_TYPES,
    MAX_LOG_HISTORY,
)

__all__ = [
    "TranslationService",
    "get_translation_service",
    "QueueAndHistoryHandler",
    "get_workflow_type_from_filename",
    "WORKFLOW_DICT",
    "MEDIA_TYPES",
    "MAX_LOG_HISTORY",
]
