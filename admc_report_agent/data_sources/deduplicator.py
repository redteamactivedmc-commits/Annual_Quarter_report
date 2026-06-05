import re
from collections import defaultdict

DELIVERABLE_TYPE_KEYWORDS = {
    "press_release": ["press release", "pr ", "media alert", "announcement", "news release"],
    "interview": ["interview", "briefing", "media brief", "journalist meet"],
    "byline": ["byline", "op-ed", "thought leadership article", "contributed article", "opinion", "contributed"],
    "event": ["event", "summit", "conference", "panel", "speaking", "webinar"],
    "social": ["social", "linkedin", "twitter", "instagram"],
}

def normalise_name(name: str) -> str:
    """Strip dates, client prefixes, issue numbers. Return first 5 meaningful words."""
    name = name.lower()
    name = re.sub(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s*\d{0,4}', '', name)
    name = re.sub(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', '', name)
    name = re.sub(r'^(admc|active dmc|denodo|knowbe4|netscout|illumio|phosphorus|qlik)\s*[-–]?\s*', '', name)
    words = name.split()
    return ' '.join(words[:5])

def detect_type(task_name: str) -> str:
    name = task_name.lower()
    for dtype, keywords in DELIVERABLE_TYPE_KEYWORDS.items():
        if any(k in name for k in keywords):
            return dtype
    return "other"

def deduplicate(tasks: list) -> list:
    """
    Group tasks by type + normalized name prefix.
    Multiple tasks from the same campaign = 1 deliverable.
    Returns list of {type, name, planned, delivered, items[]}.
    """
    groups = defaultdict(lambda: {"tasks": [], "completed": 0, "total": 0})
    for task in tasks:
        dtype = detect_type(task.get("name", ""))
        key = dtype + ":" + normalise_name(task.get("name", ""))
        groups[key]["type"] = dtype
        groups[key]["canonical"] = task.get("name", "")
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
