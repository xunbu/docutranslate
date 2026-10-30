"""Transport-independent task status and statistics."""


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
