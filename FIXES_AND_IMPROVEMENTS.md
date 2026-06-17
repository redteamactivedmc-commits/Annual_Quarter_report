# ADMC Report Agent: Critical Fixes

## Issues Identified & Solutions

### Issue 1: Asana Always Taking All Dates
**Problem:** The bot counts tasks from all dates instead of respecting the specified period.

**Root Cause:** In `asana_fetcher.py`, the `_task_in_period()` function (lines 20-41) **excludes tasks with no date information** when a period is specified, which may not match your intent. Additionally, if tasks don't have proper `due_on`, `completed_at`, or `created_at` fields, they get filtered out entirely.

**Solution:**
```python
# FILE: admc_report_agent/data_sources/asana_fetcher.py
# UPDATE the _task_in_period function to handle missing dates properly

def _task_in_period(task, period_start_date, period_end_date):
    """
    Return True if the task falls within the reporting period.
    
    Updated logic:
    - If NO period is specified: include all tasks
    - If period IS specified: use completed_at → due_on → created_at, in that order
    - Tasks with NO date at all are INCLUDED (change from current behavior)
    """
    due = _parse_date(task.get("due_on"))
    completed = _parse_date(task.get("completed_at"))
    created = _parse_date(task.get("created_at"))
    
    # Use the most recent/relevant date for filtering
    ref_date = completed or due or created
    
    # If NO period filter requested, include everything
    if not period_start_date and not period_end_date:
        return True
    
    # If no reference date exists, decide policy:
    # Option A: Include undated tasks (current issue likely here)
    if ref_date is None:
        return True  # Include tasks with no date
    
    # Apply date range filtering
    if period_start_date and ref_date < period_start_date:
        return False
    if period_end_date and ref_date > period_end_date:
        return False
    
    return True
```

**Verification:**
- Add logging in `fetch_asana_data()` to print date filtering stats
- Example log: `[DEBUG] Period filter: 2026-01-01 to 2026-03-31 | Tasks before filter: 150 | Tasks after: 45`

---

### Issue 2: PR Skills Not Integrated in Analysis
**Problem:** The bot doesn't use the PR analysis skills you've added to generate a 90-day plan.

**Root Cause:** The current AI insight generation (`ai_engine/insight_generator.py`) likely doesn't invoke the `pr-reviewer` or `pr-summary` skills. It's only using Asana task data.

**Solution - Create PR Analysis Integration:**

Create a new file: `admc_report_agent/skills/pr_analyzer.py`

```python
#!/usr/bin/env python3
"""
PR Analysis Skill Integration for 90-Day Planning
Analyzes GitHub Pull Requests to extract insights for strategic planning
"""

import anthropic
from typing import Dict, List

def analyze_pr_for_planning(pr_data: Dict, client_name: str, api_key: str) -> Dict:
    """
    Use PR summary and review skills to analyze pull requests
    and generate 90-day planning recommendations.
    
    Parameters:
    -----------
    pr_data : Dict
        Pull request data including title, description, files changed
    client_name : str
        Client name for context
    api_key : str
        Anthropic API key
        
    Returns:
    --------
    Dict with keys: summary, risks, opportunities, 90_day_recommendations
    """
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Build context from PR data
    pr_summary = pr_data.get("title", "")
    pr_description = pr_data.get("body", "")
    files_changed = pr_data.get("files_changed", [])
    
    prompt = f"""
    Analyze this GitHub PR for strategic 90-day planning context for {client_name}:
    
    **PR Title:** {pr_summary}
    
    **Description:** {pr_description}
    
    **Files Changed:** {', '.join(files_changed[:10])}  # First 10 files
    
    Provide:
    1. **PR Summary** - One paragraph overview
    2. **Technical Impact** - What this enables or improves
    3. **90-Day Roadmap Alignment** - How this fits into quarterly planning
    4. **Risk Factors** - Any technical debt or bottlenecks introduced
    5. **Recommended Follow-ups** - Next steps for the next 90 days
    
    Format as valid JSON with these keys: summary, technical_impact, roadmap_alignment, risks, follow_ups
    """
    
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )
    
    try:
        import json
        response_text = message.content[0].text
        # Extract JSON from response
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start >= 0 and end > start:
            result = json.loads(response_text[start:end])
            return result
    except:
        pass
    
    return {
        "summary": message.content[0].text,
        "error": "Could not parse structured response"
    }


def generate_90_day_plan(
    client: str,
    period: str,
    pr_analyses: List[Dict],
    deliverables: List[Dict],
    api_key: str
) -> Dict:
    """
    Generate a comprehensive 90-day plan combining PR analysis and deliverables
    """
    
    client_obj = anthropic.Anthropic(api_key=api_key)
    
    pr_summary = "\n".join([f"- {pr.get('summary', '')}" for pr in pr_analyses[:5]])
    deliverables_summary = "\n".join([f"- {d.get('name', '')}" for d in deliverables[:10]])
    
    prompt = f"""
    Create a strategic 90-day plan for {client} covering {period}:
    
    **Recent PRs & Changes:**
    {pr_summary}
    
    **Deliverables/Tasks:**
    {deliverables_summary}
    
    Provide a structured plan with:
    1. **Month 1 Focus** - Key priorities
    2. **Month 2 Focus** - Build on Month 1
    3. **Month 3 Focus** - Consolidation & preparation for next quarter
    4. **Cross-functional Dependencies** - What needs coordination
    5. **Risk Mitigation** - How to avoid delays
    6. **Success Metrics** - How to measure progress
    
    Keep each section to 2-3 bullet points max.
    """
    
    message = client_obj.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )
    
    return {
        "plan": message.content[0].text,
        "generated_at": str(datetime.now()),
        "client": client,
        "period": period,
    }
```

**Integration Point in `app.py`:**
Add this to the report generation (after line 363):

```python
# Step 2b: Fetch and analyze GitHub PRs (NEW)
pr_analyses = []
github_token = os.getenv("GITHUB_TOKEN")
if github_token:
    try:
        from skills.pr_analyzer import analyze_pr_for_planning
        # This would fetch recent PRs for the client repo
        # Example: Get PRs merged in the period
        pr_analyses = fetch_and_analyze_prs(
            client_name, github_token, period_start_date, period_end_date
        )
        print(f"  [GitHub] PR analyses: {len(pr_analyses)}")
    except Exception as e:
        print(f"  [GitHub] ERROR: {e}")
```

---

### Issue 3: Tracker Count Wrong
**Problem:** The tracker is reading all rows instead of filtering by date.

**Likely Location:** `admc_report_agent/data_sources/tracker_parser.py`

**Fix:**
```python
# Add date filtering to parse_tracker_sheet function
def parse_tracker_sheet(tracker_path: str, client_name: str, period_start: str = None, period_end: str = None) -> dict:
    """
    Parse tracker sheet with optional date filtering
    """
    import openpyxl
    from datetime import datetime
    
    wb = openpyxl.load_workbook(tracker_path, data_only=True)
    ws = wb[client_name]  # or appropriate sheet
    
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):  # Skip header
        # Extract date field (adjust column based on your tracker)
        date_field = row[4]  # Example: 5th column
        
        # Filter by period if specified
        if period_start or period_end:
            if not is_date_in_period(date_field, period_start, period_end):
                continue
        
        rows.append(row)
    
    return {
        "total_placements": len(rows),
        "rows": rows,
    }
```

---

## Configuration Updates

Add these to your `.env` file:

```env
# GitHub Integration for PR Analysis
GITHUB_TOKEN=your_github_token_here
GITHUB_REPO_OWNER=your_org_or_user
GITHUB_REPO_NAME=your_repo_name

# Enable PR Analysis in Reports
ENABLE_PR_ANALYSIS=true
ENABLE_90DAY_PLANNING=true
```

---

## Testing Checklist

- [ ] Run report generation with explicit date range (e.g., 2026-01-01 to 2026-03-31)
- [ ] Verify Asana task count matches what you see in Asana UI
- [ ] Check that tracker counts only placements in the specified period
- [ ] Verify PR analysis appears in the generated report
- [ ] Confirm 90-day plan is generated with recommendations

---

## Verification Commands

```bash
# Test Asana filtering
python -c "
from admc_report_agent.data_sources.asana_fetcher import fetch_asana_data
import os
token = os.getenv('ASANA_PAT')
result = fetch_asana_data(
    'Denodo',
    token,
    period_start='2026-01-01',
    period_end='2026-03-31'
)
print(f'Tasks found: {result[\"total_tasks\"]}')
for task in result['tasks'][:3]:
    print(f'  - {task[\"name\"]}: {task.get(\"due_on\", \"NO DATE\")}')
"

# Test report generation with dates
python admc_report_agent/admc_report_agent.py \
    --client "Denodo" \
    --period "Q1 2026" \
    --tracker "path/to/tracker.xlsx" \
    --output "test_report.pptx"
```

