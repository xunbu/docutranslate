"""File types requiring a parser rather than Markdown passthrough."""

PARSER_INPUT_SUFFIXES = frozenset({
    ".pdf", ".png", ".jpg", ".jpeg", ".jp2", ".webp", ".gif", ".bmp",
})

# One registry for discovery, SDK exports and automatic routing.
WORKFLOW_FORMATS = {
    "markdown_based": ("markdown", "markdown_zip", "html", "docx"),
    "txt": ("txt", "html"), "json": ("json", "html"),
    "xlsx": ("xlsx", "csv", "html"), "docx": ("docx", "html"),
    "srt": ("srt", "html"), "epub": ("epub", "html"),
    "html": ("html",), "ass": ("ass", "html"), "pptx": ("pptx", "html"),
}
INPUT_WORKFLOWS = {
    **{suffix: "markdown_based" for suffix in PARSER_INPUT_SUFFIXES},
    ".md": "markdown_based", ".markdown": "markdown_based", ".zip": "markdown_based",
    ".xlsx": "xlsx", ".csv": "xlsx", ".docx": "docx",
    ".html": "html", ".htm": "html", ".pptx": "pptx",
    **{"." + name: name for name in ("txt", "json", "srt", "epub", "ass")},
}
LEGACY_OFFICE_SUFFIXES = {".doc": ".docx", ".xls": ".xlsx", ".ppt": ".pptx"}


def detect_workflow(filename: str) -> str:
    from pathlib import Path
    suffix = Path(filename).suffix.lower()
    if suffix in LEGACY_OFFICE_SUFFIXES:
        raise ValueError(f"不支持 {suffix} 格式，请先转换为 {LEGACY_OFFICE_SUFFIXES[suffix]} 格式")
    return INPUT_WORKFLOWS.get(suffix, "txt")


def validate_input_format(filename: str) -> None:
    # Explicit workflow selection must not bypass the same legacy-format check.
    detect_workflow(filename)


def formats_info():
    """Public format metadata; conditional formats are resolved per result."""
    return {
        "input_formats": sorted(suffix.lstrip(".") for suffix in INPUT_WORKFLOWS),
        "output_formats_by_workflow": {key: list(value) for key, value in WORKFLOW_FORMATS.items()},
        "conditional_outputs": {"markdown_based": {"docx": "md2docx_engine must not be null"}},
    }
