import re
from collections import defaultdict

DELIVERABLE_TYPE_KEYWORDS = {
    "press_release": ["press release", "pr ", "media alert", "announcement", "news release"],
    "interview": ["interview", "briefing", "media brief", "journalist meet"],
    "byline": ["byline", "op-ed", "thought leadership article", "contributed article", "opinion", "contributed"],
    "event": ["event", "summit", "conference", "panel", "speaking", "webinar"],
    "social": ["social", "linkedin", "twitter", "instagram"],
    "media_list": ["media list", "media database", "journalist list"],
    "pitch": ["pitch", "pitching", "media pitch"],
    "report": ["report", "monthly report", "quarterly report", "coverage report"],
}

# Common filler words to strip from grouping keys
_FILLER = {"the", "a", "an", "for", "and", "or", "to", "in", "of", "on", "with", "is", "at", "by"}


def normalise_name(name: str) -> str:
    """Strip dates, client prefixes, status markers. Return meaningful words for grouping."""
    name = name.lower()
    name = re.sub(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s*\d{0,4}', '', name)
    name = re.sub(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', '', name)
    name = re.sub(r'\b\d{4}\b', '', name)
    name = re.sub(r'\b(v\d+|draft|final|revised|updated|copy|shared)\b', '', name)
    name = re.sub(r'[^\w\s]', ' ', name)
    words = [w for w in name.split() if w and w not in _FILLER]
    return ' '.join(words[:8])


def detect_type(task_name: str) -> str:
    name = task_name.lower()
    for dtype, keywords in DELIVERABLE_TYPE_KEYWORDS.items():
        if any(k in name for k in keywords):
            return dtype
    return "other"


def deduplicate(tasks: list) -> list:
    """
    Group tasks that represent the same campaign/deliverable.

    Only tasks whose type != "other" AND whose normalized names share a
    long-enough common prefix are grouped. This prevents unrelated tasks
    from being collapsed together.

    Returns list of {type, name, planned, delivered, items[]}.
    """
    groups = defaultdict(lambda: {"tasks": [], "completed": 0, "total": 0})
    for task in tasks:
        task_name = task.get("name", "")
        dtype = detect_type(task_name)
        norm = normalise_name(task_name)

        if dtype == "other":
            # Don't group "other" tasks — each is its own deliverable
            key = f"other:{task.get('gid', norm)}"
        else:
            key = dtype + ":" + norm

        groups[key]["type"] = dtype
        groups[key]["canonical"] = task_name
        groups[key]["tasks"].append(task)
        groups[key]["total"] += 1
        if task.get("completed"):
            groups[key]["completed"] += 1

    return [
        {
            "type": g["type"],
            "name": g["canonical"],
            "planned": g["total"],
            "delivered": g["completed"],
            "items": g["tasks"]
        }
        for g in groups.values()
    ]
