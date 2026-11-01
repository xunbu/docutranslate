"""Resolve public workflow options identically for SDK, HTTP and MCP."""
from pathlib import Path

from pydantic import TypeAdapter

from docutranslate.config import CONVERT_ENGINE
from docutranslate.core.file_types import detect_workflow, validate_input_format, PARSER_INPUT_SUFFIXES
from docutranslate.core.schemas import TranslatePayload


INHERIT = "inherit"

# An empty string is an explicit override only for these text options (the
# v1.7.11 contract). For every other option an empty string means "not
# provided", which is how older MCP/HTTP clients signalled "use the default".
EMPTY_TEXT_OVERRIDE_FIELDS = frozenset({"separator", "custom_prompt"})


def normalize_empty_text(name: str, value):
    """Treat empty text as omitted unless the option documents empty as a value."""
    if isinstance(value, str) and value == "" and name not in EMPTY_TEXT_OVERRIDE_FIELDS:
        return None
    return value


def normalize_options(options, filename: str):
    """Resolve auto before validation; retain explicit empty/false/zero/null values."""
    validate_input_format(filename)
    data = dict(options)
    if data.get("workflow_type", "auto") == "auto":
        data["workflow_type"] = detect_workflow(filename)
    if data["workflow_type"] == "json" and data.get("json_paths") is None:
        data["json_paths"] = ["$..*"]
    if data["workflow_type"] == "markdown_based" and data.get("convert_engine") is None:
        data["convert_engine"] = (
            (CONVERT_ENGINE if CONVERT_ENGINE in ("mineru", "mineru_deploy") else "mineru")
            if Path(filename).suffix.lower() in PARSER_INPUT_SUFFIXES else "identity"
        )
    return data


def resolve_payload(options, filename: str):
    return TypeAdapter(TranslatePayload).validate_python(normalize_options(options, filename))


def resolve_auto_payload(payload, filename: str):
    # Defaults on AutoWorkflowParams must not mask the target workflow's defaults.
    data = payload.model_dump(exclude_unset=True)
    nullable = {"md2docx_engine", "read_timeout", "non_stream_timeout"}
    data = {k: v for k, v in data.items() if v is not None or k in nullable}
    return resolve_payload(data, filename)
