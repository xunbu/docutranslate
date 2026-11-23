"""Transport-independent task status and statistics."""

_ZERO_TOTALS = {"request_count": 0, "unresolved_errors": 0, "unresolved_error_rate": 0.0}


def _as_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _as_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def statistics_totals(statistics) -> dict:
    """Read the aggregate counters out of a workflow statistics dict.

    ``Workflow.get_statistics()`` returns ``{"glossary", "translation", "total"}``.
    A surface may only hold partial information (or none at all), so every field
    falls back to its zero value instead of raising on the status endpoint.
    """
    total = statistics.get("total") if isinstance(statistics, dict) else None
    if not isinstance(total, dict):
        return dict(_ZERO_TOTALS)
    return {
        "request_count": _as_int(total.get("request_count")),
        "unresolved_errors": _as_int(total.get("unresolved_errors")),
        "unresolved_error_rate": _as_float(total.get("unresolved_error_rate")),
    }


def is_partial(state) -> bool:
    """True when a finished task delivered files but some chunks fell back to source text.

    A chunk whose requests all fail is replaced by its source text, so the export
    still succeeds while parts of the document stay untranslated. Such a result is
    downloadable (``download_ready``) and is not an error (``error_flag``), but
    callers must be able to tell it apart from a complete translation.
    """
    if state.get("is_processing") or state.get("cancelled") or state.get("error_flag"):
        return False
    if not state.get("download_ready"):
        return False
    return statistics_totals(task_statistics(state))["unresolved_errors"] > 0


def task_status(state):
    if state.get("is_processing"):
        return "running"
    if state.get("cancelled"):
        return "cancelled"
    if state.get("error_flag"):
        return "error"
    return "completed" if state.get("download_ready") else "idle"


def task_statistics(state):
    if state.get("statistics") is not None:
        return state["statistics"]
    workflow = state.get("workflow_instance")
    if workflow is not None:
        try:
            return workflow.get_statistics()
        except Exception:
            pass
    return default_statistics()


def default_statistics():
    return {
        "glossary": None, "translation": None,
        "total": {"input_tokens": 0, "cached_tokens": 0, "output_tokens": 0,
                  "reasoning_tokens": 0, "total_tokens": 0, "request_count": 0,
                  "unresolved_errors": 0, "unresolved_error_rate": 0.0},
    }
