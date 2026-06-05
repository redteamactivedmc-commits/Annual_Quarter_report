"""
ADMC Report Agent — Brand configuration and constants.
"""

ADMC_COLORS = {
    "teal_primary": "0097B2",
    "teal_dark": "007A91",
    "teal_light": "E8F7FA",
    "teal_mid": "B3E0EA",
    "white": "FFFFFF",
    "navy_text": "1A2B4A",
    "dark_title": "0D1B2E",
    "gray_light": "F5F5F5",
    "gray_border": "CCCCCC",
    "metric_blue": "0097B2",
    "table_header": "0097B2",
    "table_alt_row": "E8F7FA",
}

SLIDE_WIDTH = 13.33  # inches (widescreen 16:9)
SLIDE_HEIGHT = 7.5   # inches

FONTS = {
    "title_font": "Montserrat",
    "body_font": "Montserrat",
    "metric_font": "Montserrat",
    "fallback_font": "Arial",
}

FONT_SIZES = {
    "cover_title": 44,
    "cover_subtitle": 18,
    "section_title": 36,
    "slide_title": 28,
    "body": 14,
    "table_header": 12,
    "table_body": 11,
    "metric_number": 48,
    "metric_label": 13,
    "footer": 9,
    "caption": 10,
}

SECTIONS = [
    "Cover Page",
    "Contents",
    "Campaign Overview",
    "Coverage Highlights",
    "Deliverables Overview",
    "Coverage Analysis",
    "Media Relations",
    "Driving the Narrative",
    "Special Initiatives",
    "Observation / Feedback",
    "Strategic Recommendations",
    "90-Day Plan",
    "Thank You",
]

DELIVERABLE_TYPE_KEYWORDS = {
    "press_release": ["press release", "pr ", "media alert", "announcement", "news release"],
    "interview": ["interview", "briefing", "media brief", "journalist meet"],
    "byline": ["byline", "op-ed", "thought leadership article", "contributed article"],
    "event": ["event", "summit", "conference", "panel", "speaking", "webinar"],
    "social": ["social", "linkedin", "twitter", "instagram"],
}

INSIGHT_SYSTEM_PROMPT = """You are a senior communications strategist at Active DMC, a premium PR agency in Dubai.
Generate strategic insights for client communications reports.

INSIGHT FRAMEWORK — every insight must follow:
1. WHAT happened (the specific fact or data point)
2. WHY it happened (the reason or cause)
3. WHAT IT MEANS (the strategic implication for the client)

TONE: Premium consulting — concise, strategic, non-generic.
LANGUAGE: Professional English. GCC/Middle East context where relevant.
OUTPUT: Return only valid JSON, no markdown, no preamble."""
