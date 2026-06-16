import requests
from datetime import datetime, date
from .deduplicator import deduplicate

ASANA_BASE_URL = "https://app.asana.com/api/1.0"

TASK_OPT_FIELDS = "name,completed,completed_at,due_on,created_at,notes,assignee.name,num_subtasks,resource_subtype"


def _parse_date(date_str):
    """Parse a date string (YYYY-MM-DD) into a date object. Returns None on failure."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _task_in_period(task, period_start_date, period_end_date):
    """
    Return True if the task falls within the reporting period.

    A task is included if its completed_at OR due_on date falls within
    [period_start_date, period_end_date]. Tasks with no date at all are
    excluded when a date range is specified, to avoid inflating counts.
    """
    due = _parse_date(task.get("due_on"))
    completed = _parse_date(task.get("completed_at"))

    created = _parse_date(task.get("created_at"))
    ref_date = completed or due or created

    if ref_date is None:
        return False

    if period_start_date and ref_date < period_start_date:
        return False
    if period_end_date and ref_date > period_end_date:
        return False
    return True


def _get_all_pages(url, headers, params, timeout=30):
    """
    Fetch all pages from an Asana paginated endpoint.
    Returns the combined list of data items.
    """
    all_items = []
    next_page_url = url
    current_params = dict(params)

    while next_page_url:
        resp = requests.get(next_page_url, headers=headers, params=current_params, timeout=timeout)
        resp.raise_for_status()
        body = resp.json()
        all_items.extend(body.get("data", []))

        # After the first request, pagination uses the full URI from next_page
        next_page_info = body.get("next_page")
        if next_page_info and next_page_info.get("uri"):
            next_page_url = "https://app.asana.com" + next_page_info["uri"]
            current_params = {}  # params are embedded in the URI
        else:
            next_page_url = None

    return all_items


def fetch_asana_data(client_name: str, asana_token: str, period_start: str = None, period_end: str = None) -> dict:
    """
    Fetch deliverables from Asana for the given client.

    Searches ALL workspaces for projects whose name contains the client name
    (case-insensitive), collects tasks from every matching project, optionally
    filters by reporting period, and returns deduplicated deliverables.

    Parameters
    ----------
    client_name : str
        The client name to search for (e.g. "Denodo").
    asana_token : str
        Asana Personal Access Token.
    period_start : str, optional
        Start date of reporting period as "YYYY-MM-DD". Tasks before this date
        are excluded.
    period_end : str, optional
        End date of reporting period as "YYYY-MM-DD". Tasks after this date
        are excluded.

    Returns
    -------
    dict with keys:
        projects_found  — list of {name, gid} for matched projects
        tasks           — all tasks (after date filtering)
        deliverables    — deduplicated deliverable groups
        total_tasks     — count of tasks included
        period_start    — the start date used (or None)
        period_end      — the end date used (or None)
        error           — error message if something went wrong (absent on success)
    """
    headers = {"Authorization": f"Bearer {asana_token}"}
    client_lower = client_name.lower()

    # Parse period dates
    period_start_date = _parse_date(period_start)
    period_end_date = _parse_date(period_end)

    # --- Step 1: Get ALL workspaces ---
    try:
        workspaces = _get_all_pages(
            f"{ASANA_BASE_URL}/workspaces", headers, {"limit": 100}
        )
    except requests.RequestException as e:
        return {
            "projects_found": [],
            "tasks": [],
            "deliverables": [],
            "total_tasks": 0,
            "error": f"Failed to fetch Asana workspaces: {e}",
        }

    if not workspaces:
        return {
            "projects_found": [],
            "tasks": [],
            "deliverables": [],
            "total_tasks": 0,
            "error": "No Asana workspaces found. Check your token.",
        }

    # --- Step 2: Search every workspace for matching projects ---
    matching_projects = []

    for ws in workspaces:
        ws_gid = ws["gid"]
        try:
            projects = _get_all_pages(
                f"{ASANA_BASE_URL}/workspaces/{ws_gid}/projects",
                headers,
                {"opt_fields": "name,gid,archived", "limit": 100},
            )
        except requests.RequestException:
            continue

        for p in projects:
            # Skip archived projects
            if p.get("archived"):
                continue
            pname = p.get("name", "")
            if client_lower in pname.lower():
                matching_projects.append({
                    "gid": p["gid"],
                    "name": pname,
                    "workspace_gid": ws_gid,
                })

    if not matching_projects:
        return {
            "projects_found": [],
            "tasks": [],
            "deliverables": [],
            "total_tasks": 0,
            "error": (
                f"No projects found matching '{client_name}' across "
                f"{len(workspaces)} workspace(s). "
                f"Make sure the Asana token has access and the project name "
                f"contains '{client_name}'."
            ),
        }

    # --- Step 3: Collect tasks from ALL matching projects ---
    all_tasks = []
    seen_task_gids = set()  # avoid duplicates if a task is multi-homed

    for proj in matching_projects:
        try:
            tasks = _get_all_pages(
                f"{ASANA_BASE_URL}/projects/{proj['gid']}/tasks",
                headers,
                {"opt_fields": TASK_OPT_FIELDS, "limit": 100},
            )
        except requests.RequestException:
            continue

        for t in tasks:
            # Skip sections and milestones — they are not real deliverables
            subtype = t.get("resource_subtype", "default_task")
            if subtype in ("section", "milestone"):
                continue

            if t["gid"] not in seen_task_gids:
                seen_task_gids.add(t["gid"])
                t["_source_project"] = proj["name"]
                all_tasks.append(t)

                # Fetch subtasks if present — deliverables may be nested
                if t.get("num_subtasks", 0) > 0:
                    try:
                        subtasks = _get_all_pages(
                            f"{ASANA_BASE_URL}/tasks/{t['gid']}/subtasks",
                            headers,
                            {"opt_fields": TASK_OPT_FIELDS, "limit": 100},
                        )
                        for st in subtasks:
                            st_subtype = st.get("resource_subtype", "default_task")
                            if st_subtype in ("section", "milestone"):
                                continue
                            if st["gid"] not in seen_task_gids:
                                seen_task_gids.add(st["gid"])
                                st["_source_project"] = proj["name"]
                                st["_parent_task"] = t.get("name", "")
                                all_tasks.append(st)
                    except requests.RequestException:
                        pass

    # --- Step 4: Filter by reporting period ---
    if period_start_date or period_end_date:
        filtered_tasks = [
            t for t in all_tasks
            if _task_in_period(t, period_start_date, period_end_date)
        ]
    else:
        filtered_tasks = all_tasks

    # --- Step 5: Deduplicate ---
    deliverables = deduplicate(filtered_tasks)

    return {
        "projects_found": [{"name": p["name"], "gid": p["gid"]} for p in matching_projects],
        "tasks": filtered_tasks,
        "deliverables": deliverables,
        "total_tasks": len(filtered_tasks),
        "period_start": period_start,
        "period_end": period_end,
    }
