import requests
from .deduplicator import deduplicate

ASANA_BASE_URL = "https://app.asana.com/api/1.0"

def fetch_asana_data(client_name: str, asana_token: str) -> dict:
    """
    Fetch deliverables from Asana for the given client.
    Returns dict with tasks list and deduplicated deliverables.
    """
    headers = {"Authorization": f"Bearer {asana_token}"}

    # Get workspaces
    resp = requests.get(f"{ASANA_BASE_URL}/workspaces", headers=headers, timeout=30)
    resp.raise_for_status()
    workspaces = resp.json().get("data", [])

    if not workspaces:
        return {"tasks": [], "deliverables": [], "error": "No workspaces found"}

    workspace_gid = workspaces[0]["gid"]

    # Search for client project
    resp = requests.get(
        f"{ASANA_BASE_URL}/workspaces/{workspace_gid}/projects",
        headers=headers,
        params={"opt_fields": "name,gid"},
        timeout=30,
    )
    resp.raise_for_status()
    projects = resp.json().get("data", [])

    # Find project matching client name
    target_project = None
    client_lower = client_name.lower()
    for p in projects:
        if client_lower in p.get("name", "").lower():
            target_project = p
            break

    if not target_project:
        return {"tasks": [], "deliverables": [], "error": f"No project found for '{client_name}'"}

    # Get tasks from project
    resp = requests.get(
        f"{ASANA_BASE_URL}/projects/{target_project['gid']}/tasks",
        headers=headers,
        params={"opt_fields": "name,completed,due_on,notes,assignee.name"},
        timeout=30,
    )
    resp.raise_for_status()
    tasks = resp.json().get("data", [])

    # Deduplicate
    deliverables = deduplicate(tasks)

    return {
        "project_name": target_project.get("name", ""),
        "tasks": tasks,
        "deliverables": deliverables,
        "total_tasks": len(tasks),
    }
