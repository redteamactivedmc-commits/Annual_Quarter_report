import json
import anthropic

INSIGHT_SYSTEM_PROMPT = """You are a senior communications strategist at Active DMC, a premium PR agency in Dubai.
Generate strategic insights for client communications reports.

INSIGHT FRAMEWORK — every insight must follow:
1. WHAT happened (the specific fact or data point)
2. WHY it happened (the reason or cause)
3. WHAT IT MEANS (the strategic implication for the client)

TONE: Premium consulting — concise, strategic, non-generic.
LANGUAGE: Professional English. GCC/Middle East context where relevant.
OUTPUT: Return only valid JSON, no markdown, no preamble."""

SECTION_PROMPTS = {
    "campaign_overview": "Analyze the overall campaign performance. Focus on total placements, tier distribution, language split, and reach metrics.",
    "coverage_highlights": "Identify the most significant media placements and explain their strategic value.",
    "deliverables_analysis": "Analyze planned vs delivered activities. Note completion rates and any gaps.",
    "coverage_analysis": "Break down coverage by tier, language, and media type. Identify patterns and opportunities.",
    "media_relations": "Assess media engagement quality, journalist relationships, and publication targeting effectiveness.",
    "narrative": "Analyze how key messages and themes were communicated across placements. Identify messaging evolution and strategic communications themes. This is the 'Driving the Narrative' section — focus on storytelling arc.",
    "observation": "Generate 'What Went Well' (3 bullets) and 'What Could Be Better' (4 bullets) observations. Return as JSON with keys 'went_well' (list of strings) and 'improve' (list of strings).",
    "recommendations": "Generate 5 specific, actionable strategic recommendations based on the data. Return as JSON with key 'recommendations' (list of {title, description}).",
    "ninety_day_plan": "Create a 90-day forward plan with monthly breakdown. For each of the next 3 months, list planned interviews and byline topics. Return as JSON with key 'months' (list of {month, interviews: [topic], bylines: [topic]}).",
}


def generate_section_insights(
    client: str,
    period: str,
    section_name: str,
    data_context: dict,
    api_key: str,
) -> dict:
    """
    Call Claude API to generate structured insights for one report section.
    Returns parsed JSON dict.
    """
    client_api = anthropic.Anthropic(api_key=api_key)

    section_guidance = SECTION_PROMPTS.get(section_name, "Provide strategic insights for this section.")

    if section_name == "observation":
        json_schema = '{"went_well": ["point1", ...], "improve": ["point1", ...]}'
    elif section_name == "recommendations":
        json_schema = '{"recommendations": [{"title": "...", "description": "..."}, ...]}'
    elif section_name == "ninety_day_plan":
        json_schema = '{"months": [{"month": "Month 1", "interviews": ["topic"], "bylines": ["topic"]}, ...]}'
    else:
        json_schema = '{"insights": [{"what": "...", "why": "...", "implication": "..."}], "summary": "..."}'

    user_prompt = f"""Generate insights for the "{section_name}" section of an Active DMC communications report.

CLIENT: {client}
REPORTING PERIOD: {period}

SECTION GUIDANCE: {section_guidance}

DATA:
{json.dumps(data_context, indent=2, default=str)}

Return ONLY a JSON object matching this structure (no markdown, no preamble):
{json_schema}

Be specific to the data provided — never generic."""

    response = client_api.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=INSIGHT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    return json.loads(raw)


def generate_all_insights(
    client: str,
    period: str,
    tracker_data: dict,
    deliverables_data: list,
    api_key: str,
    progress_callback=None,
) -> dict:
    """
    Generate insights for all report sections.
    Returns dict keyed by section name.
    """
    sections = [
        "campaign_overview",
        "coverage_highlights",
        "deliverables_analysis",
        "coverage_analysis",
        "media_relations",
        "narrative",
        "observation",
        "recommendations",
        "ninety_day_plan",
    ]

    # Build data context for each section
    base_context = {
        "client": client,
        "period": period,
        "total_placements": tracker_data.get("total_placements", 0),
        "tier1_count": tracker_data.get("tier1_count", 0),
        "tier2_count": tracker_data.get("tier2_count", 0),
        "english_count": tracker_data.get("english_count", 0),
        "arabic_count": tracker_data.get("arabic_count", 0),
        "unique_pr_campaigns": tracker_data.get("unique_pr_campaigns", 0),
        "total_reach": tracker_data.get("total_reach", 0),
        "media_type_breakdown": tracker_data.get("media_type_breakdown", {}),
        "top_publications": tracker_data.get("top_publications", []),
        "interview_count": tracker_data.get("interview_count", 0),
        "byline_count": tracker_data.get("byline_count", 0),
    }

    if deliverables_data:
        base_context["deliverables"] = [
            {"type": d["type"], "name": d["name"], "planned": d["planned"], "delivered": d["delivered"]}
            for d in deliverables_data
        ]

    results = {}
    for i, section in enumerate(sections):
        if progress_callback:
            progress_callback(section, i, len(sections))

        try:
            result = generate_section_insights(client, period, section, base_context, api_key)
            results[section] = result
        except Exception as e:
            results[section] = {"error": str(e), "insights": [], "summary": f"[Insight generation failed: {e}]"}

    return results
