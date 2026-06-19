import json
import os
import anthropic


def _load_skills_context():
    """Load PR skills from the skills/ directory to enrich AI prompts."""
    skills_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills")
    context_parts = []
    for fname in ("Media_Outreach_SKILL.md", "regional-fit-checks.md", "outreach-templates.md"):
        fpath = os.path.join(skills_dir, fname)
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    context_parts.append(f.read())
            except Exception:
                pass
    return "\n\n".join(context_parts)


_SKILLS_CONTEXT = _load_skills_context()

INSIGHT_SYSTEM_PROMPT = """You are a senior communications strategist at Active DMC, a premium PR agency in Dubai.
You handle PR for technology clients in the GCC region, with primary focus on UAE and KSA markets.
Generate strategic insights for client communications reports.

INSIGHT FRAMEWORK — every insight must follow:
1. WHAT happened (the specific fact or data point)
2. WHY it happened (the reason or cause)
3. WHAT IT MEANS (the strategic implication for the client)

═══════════════════════════════════════════════════════════
REGIONAL FIT — GCC / UAE / KSA CONTEXT (apply to ALL sections)
═══════════════════════════════════════════════════════════
Every insight must be tested: Does this affect local buyers, regulators, or sectors?

UAE fit signals:
  - Enterprise digitization, critical infrastructure (finance, telecom, govt, transport)
  - Cloud / AI / cybersecurity adoption curves
  - Regulatory and resilience frameworks (CBUAE, TDRA, DFF, ADGM, DIFC)

KSA fit signals:
  - National programs (Vision 2030, NTP, NEOM, giga-projects)
  - Sector modernization, localization (Saudization / data-residency)
  - Industrial, energy, and mega-project relevance

GCC-wide fit signals:
  - Cross-market trends, shared risk patterns, region-wide operational issues
  - Regional regulatory convergence or divergence

CRITICAL RULE: Never force regionalization. If the local angle is not genuine,
say so explicitly. Forced localization is a common failure mode — flag it rather
than fabricate a connection.

═══════════════════════════════════════════════════════════
EDITORIAL QUALITY RULES (apply to ALL generated text)
═══════════════════════════════════════════════════════════
- Lead with WHY the story matters NOW (timeliness first)
- One dominant angle per insight — do not mix multiple themes
- Measured claims backed by data — no hype verbs ("revolutionize",
  "game-changing", "unprecedented"), no buzzwords
- Facts over adjectives — concrete numbers beat superlatives
- Separate FACT from INTERPRETATION clearly
- NEVER invent statistics, policies, company names, or examples
- If data is missing or ambiguous, flag it — prefer omission over uncertainty
- Tone: editor-friendly, not press-release language

═══════════════════════════════════════════════════════════
MEDIA OUTREACH INTELLIGENCE (for narrative / media sections)
═══════════════════════════════════════════════════════════
Angle selection priority (in order):
  1. Timely market relevance
  2. Strong data point
  3. Local or sector impact
  4. Credible spokesperson availability
  5. Event visibility / news-peg

Reject angles built on: product descriptions, vague leadership claims,
generic milestones without context, or unsubstantiated "first-in-region" assertions.

Pitch-type awareness: distinguish coverage that came from interviews vs bylines
vs press releases vs reactive media comments. Each type signals different
relationship depth and editorial influence.

TONE: Premium consulting — concise, strategic, non-generic.
LANGUAGE: Professional English. GCC/Middle East context where genuinely relevant.
OUTPUT: Return only valid JSON, no markdown, no preamble."""

SECTION_PROMPTS = {
    "campaign_overview": """Analyze the overall campaign performance. Focus on total placements, tier distribution,
language split, and reach metrics.

REGIONAL FIT: Frame performance within the GCC media landscape — how does the tier split
compare to what is typical for this market? Is the English/Arabic ratio appropriate for the
client's target audience in UAE/KSA/GCC?

EDITORIAL RULES: Lead with the single most significant performance metric and why it matters
now. Use exact numbers from the data — no rounding that obscures meaning. If any metric is
missing or looks anomalous, flag it rather than interpreting around it.""",

    "coverage_highlights": """Identify the most significant media placements and explain their strategic value.

ANGLE SELECTION: Prioritize placements by (1) publication tier and audience relevance,
(2) strength of the data point or quote, (3) local/sector impact, (4) spokesperson visibility.
Reject highlights based solely on volume — a single Tier 1 exclusive outweighs ten generic pickups.

REGIONAL FIT: Note whether top placements reached GCC decision-makers in target sectors.
Flag coverage in key regional titles (Arabian Business, Gulf News, Zawya, Argaam, Al Arabiya, etc.)
vs international outlets with GCC readership.

PITCH-TYPE AWARENESS: Where possible, note whether the highlight came from an interview,
byline, press release pickup, or reactive comment — this signals editorial relationship depth.""",

    "deliverables_analysis": """Analyze planned vs delivered activities. Note completion rates and any gaps.

EDITORIAL RULES: Present completion rates as fact, then interpret separately. Do not spin
shortfalls as positives. If deliverables exceeded plan, explain the cause (opportunistic
placements? scope change?) rather than just celebrating the number.

REGIONAL FIT: Consider whether the deliverable mix (interviews vs bylines vs press releases)
is appropriate for GCC media norms. Arabic-language deliverables often require different
lead times and editorial relationships — note if the Arabic pipeline is on track.

FLAG: If any deliverable category shows zero or near-zero delivery, call it out explicitly
with a recommended corrective action.""",

    "coverage_analysis": """Break down coverage by tier, language, and media type. Identify patterns and opportunities.

TIER STRATEGY: Analyze Tier 1 vs Tier 2 distribution. In GCC markets, Tier 1 placements
carry outsized influence with enterprise buyers and government stakeholders. Is the current
tier mix aligned with the client's objectives?

LANGUAGE SPLIT: Evaluate English/Arabic ratio against client goals. Arabic placements often
have disproportionate reach in KSA and broader GCC government/enterprise audiences.
English dominance may signal missed Arabic-market opportunities.

MEDIA TYPE: Distinguish online vs print vs broadcast. Note whether coverage is concentrated
in one type or diversified. Trade/vertical publications often carry more weight with
sector buyers than general business press.

OPPORTUNITY GAPS: Identify specific publication types, languages, or tiers that are
underrepresented and explain why filling that gap would matter.""",

    "media_relations": """Assess media engagement quality, journalist relationships, and publication targeting effectiveness.

PITCH-TYPE ANALYSIS: Categorize coverage by origin — interviews, bylines, press release
pickups, reactive comments. Each type signals different relationship depth:
  - Interviews = strong journalist relationship, high editorial trust
  - Bylines = thought-leadership positioning, editorial credibility
  - Press releases = baseline distribution, lower editorial influence
  - Reactive comments = newsjacking ability, spokesperson readiness

ANGLE QUALITY CHECK: Were the angles pitched genuinely timely and market-relevant?
Or did coverage rely on product announcements and generic milestones?
Flag any coverage that reads like press-release language — it signals the pitch
did not add editorial value.

REGIONAL MEDIA CONTEXT: GCC media landscape has distinct characteristics — strong
government-linked publications, growing digital-first outlets, influential Arabic
business press. Assess whether the media list reflects these dynamics.

RELATIONSHIP DEPTH: Look beyond placement counts. Repeat coverage in the same
publication suggests a maturing journalist relationship. Note any new outlets secured.""",

    "narrative": """Analyze how key messages and themes were communicated across placements.
This is the 'Driving the Narrative' section — focus on the storytelling arc.

ANGLE DISCIPLINE: Identify the ONE dominant narrative thread across the period's coverage.
Do not mix multiple themes — if coverage spanned several topics, note the primary thread
and flag fragmentation as a risk.

REGIONAL RELEVANCE: Test each narrative theme — does it connect to a genuine GCC concern?
  - UAE: digital transformation, critical infrastructure resilience, regulatory compliance
  - KSA: Vision 2030 alignment, sector modernization, localization mandates
  - GCC-wide: cross-border trends, shared risk patterns
If the local angle is not genuine, say so — forced regionalization weakens credibility.

EDITORIAL QUALITY: Assess whether the narrative tone across placements was editor-friendly
or press-release-heavy. Strong narratives lead with market context, not product features.
Note any messaging evolution — did the narrative sharpen or drift over the period?

TIMELINESS: Was the narrative pegged to current market conditions, regulatory shifts,
or regional events? Or was it generic enough to have run in any quarter?""",

    "observation": """Generate 'What Went Well' (3 bullets) and 'What Could Be Better' (4 bullets) observations.
Return as JSON with keys 'went_well' (list of strings) and 'improve' (list of strings).

WHAT WENT WELL — rules:
  - Each bullet must cite specific evidence: publication name, tier, reach figure, or metric
  - Good example: "Secured 3 Tier 1 interviews in Arabian Business, Gulf Business, and Forbes ME,
    reaching an estimated 2.1M readers"
  - Bad example: "Good media coverage this quarter" (too vague)
  - Reference the angle quality: was the coverage driven by timely market relevance or just volume?

WHAT COULD BE BETTER — rules:
  - Each bullet must be actionable, not vague criticism
  - Good example: "Arabic coverage was 15% of total — increase Arabic pitching by targeting
    Argaam, Al Arabiya, and Zahrat Al Khaleej with localized angles"
  - Bad example: "Need more Arabic coverage" (no action, no specifics)
  - Check these common failure modes and flag any that apply:
    * Forced localization (GCC angle felt manufactured rather than genuine)
    * Press-release tone in pitched content (not editor-friendly)
    * Mixed angles (multiple themes crammed into single pitches)
    * Over-reliance on one pitch type (e.g., all press releases, no interviews)
  - Was the regional fit genuine? Was the tone consistently editorial?""",

    "recommendations": """Generate 5 specific, actionable strategic recommendations based on the data.
Return as JSON with key 'recommendations' (list of {title, description}).

EACH RECOMMENDATION must follow this structure:
  - WHAT TO DO: Specific, concrete action (not "improve media relations")
  - WHY IT WORKS: Evidence from the data or GCC market context that supports this action
  - EXPECTED OUTCOME: What success looks like if executed

STRATEGIC DIMENSIONS to consider:
  1. PITCH TYPE MIX: Is the balance of interviews vs bylines vs press releases optimal?
     Interviews build spokesperson profile; bylines establish thought leadership;
     press releases maintain baseline visibility. Recommend rebalancing if needed.
  2. PUBLICATION TIER STRATEGY: Should the client push for more Tier 1 exclusives
     (higher impact, longer lead time) or broaden Tier 2 volume (faster, wider reach)?
  3. LANGUAGE OPTIMIZATION: Is the English/Arabic split serving the client's GCC goals?
     Arabic placements are critical for KSA government and enterprise audiences.
  4. GCC MARKET CONTEXT: Reference specific regional dynamics — regulatory shifts,
     sector trends, upcoming events, national program milestones.
  5. NARRATIVE SHARPENING: Is the client's story focused enough to cut through?
     Recommend specific angle refinements tied to market timing.

QUALITY BAR: Reject recommendations that are generic ("leverage social media",
"increase thought leadership"). Every recommendation must be specific to THIS client's
data and THIS market context.""",

    "ninety_day_plan": """Create a 90-day forward plan with monthly breakdown.
For each of the next 3 months, list planned interviews and byline topics.
Return as JSON with key 'months' (list of {month, interviews: [topic], bylines: [topic]}).

INTERVIEW TOPICS should target:
  - Timely market relevance (what GCC buyers/regulators care about RIGHT NOW)
  - Upcoming regional events, policy cycles, or market moments
  - Data points or research the client can credibly own
  - Avoid generic "digital transformation" angles — be specific to sector and timing

BYLINE TOPICS should:
  - Address a sector issue with an original perspective (not a product pitch)
  - Offer genuine insight that an editor would commission independently
  - Connect to GCC market dynamics — regulatory changes, adoption trends, workforce shifts
  - Be scoped tightly enough to write in 800-1000 words

MONTHLY THEMATIC FOCUS:
  - Each month should have a clear theme that connects its interviews and bylines
  - Consider: Q3/Q4 budget cycles, Ramadan/Eid timing, GITEX/LEAP/regional events,
    regulatory announcement windows, earnings seasons
  - Build momentum — Month 1 establishes the narrative, Month 2 deepens it,
    Month 3 pivots to next quarter's opportunity

PITCH TYPE BALANCE: Ensure the plan includes a healthy mix across the 90 days,
not just one format. If the prior period was heavy on press releases, skew toward
interviews and bylines to build editorial depth.""",
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

    skills_block = ""
    if section_name in ("ninety_day_plan", "recommendations", "narrative", "media_relations") and _SKILLS_CONTEXT:
        skills_block = f"""

PR AGENCY SKILLS & REGIONAL CONTEXT (use these to ground your output):
{_SKILLS_CONTEXT[:3000]}
"""

    user_prompt = f"""Generate insights for the "{section_name}" section of an Active DMC communications report.

CLIENT: {client}
REPORTING PERIOD: {period}
MARKET FOCUS: GCC region — primary focus on UAE and KSA

SECTION GUIDANCE: {section_guidance}
{skills_block}
DATA:
{json.dumps(data_context, indent=2, default=str)}

Return ONLY a JSON object matching this structure (no markdown, no preamble):
{json_schema}

Be specific to the data provided and the GCC/UAE/KSA market context — never generic."""

    models_to_try = [
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
    ]
    response = None
    last_error = None
    for model_id in models_to_try:
        try:
            response = client_api.messages.create(
                model=model_id,
                max_tokens=4096,
                system=INSIGHT_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            break
        except anthropic.NotFoundError:
            last_error = f"Model {model_id} not available"
            continue
    if response is None:
        raise RuntimeError(last_error or "No Claude model available")

    if not response.content:
        raise RuntimeError("Empty response from Claude API")
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
            {
                "type": d.get("type", "other"),
                "name": d.get("name", ""),
                "planned": d.get("planned", 0),
                "delivered": d.get("delivered", 0),
            }
            for d in deliverables_data
            if isinstance(d, dict)
        ]

    results = {}
    for i, section in enumerate(sections):
        if progress_callback:
            progress_callback(section, i, len(sections))

        try:
            result = generate_section_insights(client, period, section, base_context, api_key)
            results[section] = result
            print(f"  [AI] {section}: OK ({len(str(result))} chars)")
        except Exception as e:
            print(f"  [AI] {section}: FAILED — {e}")
            is_auth_error = "401" in str(e) or "authentication" in str(e).lower() or "api-key" in str(e).lower() or "api_key" in str(e).lower()
            if is_auth_error:
                friendly = "AI insights unavailable — please check your Anthropic API key in Settings."
            else:
                friendly = "AI insights could not be generated for this section."
            fallback = {"error": str(e), "insights": [], "summary": friendly}
            if section == "observation":
                fallback["went_well"] = ["Data not available — see coverage stats for this period."]
                fallback["improve"] = ["Review pending — AI insights require a valid API key."]
            elif section == "recommendations":
                fallback["recommendations"] = []
            elif section == "ninety_day_plan":
                fallback["months"] = []
            results[section] = fallback

    return results
