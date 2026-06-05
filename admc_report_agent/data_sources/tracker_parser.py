import openpyxl
from collections import Counter
from .deduplicator import normalise_name

def parse_tracker(file_path: str) -> dict:
    """
    Parse ADMC_clients_{Client}_tracker.xlsx
    Expected columns: S N, Date, Publication, Headline, Media Type, Language,
                      Spokesperson, Source, Reach, Tier, Print/Online, For PIV
    Returns a dict with summary stats and raw rows.
    """
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active

    rows_data = []
    headers = []
    header_map = {}

    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            headers = [str(h).strip().lower() if h else "" for h in row]
            # Build flexible header mapping
            for idx, h in enumerate(headers):
                if "date" in h:
                    header_map["date"] = idx
                elif "publication" in h:
                    header_map["publication"] = idx
                elif "headline" in h:
                    header_map["headline"] = idx
                elif "media type" in h or "media_type" in h:
                    header_map["media_type"] = idx
                elif "language" in h or "lang" in h:
                    header_map["language"] = idx
                elif "spokesperson" in h or "spoke" in h:
                    header_map["spokesperson"] = idx
                elif "source" in h:
                    header_map["source"] = idx
                elif "reach" in h:
                    header_map["reach"] = idx
                elif "tier" in h:
                    header_map["tier"] = idx
                elif "print" in h or "online" in h:
                    header_map["print_online"] = idx
            continue

        if not any(row):
            continue

        entry = {}
        for field, idx in header_map.items():
            if idx < len(row):
                entry[field] = row[idx]
        rows_data.append(entry)

    wb.close()

    # Compute summary statistics
    total_placements = len(rows_data)

    languages = Counter()
    tiers = Counter()
    media_types = Counter()
    print_online = Counter()
    publications = Counter()
    sources = Counter()
    total_reach = 0
    reach_available = 0

    for r in rows_data:
        lang = str(r.get("language", "")).strip()
        if lang:
            languages[lang] += 1

        tier = str(r.get("tier", "")).strip()
        if tier:
            tiers[tier] += 1

        mt = str(r.get("media_type", "")).strip()
        if mt:
            media_types[mt] += 1

        po = str(r.get("print_online", "")).strip()
        if po:
            print_online[po] += 1

        pub = str(r.get("publication", "")).strip()
        if pub:
            publications[pub] += 1

        src = str(r.get("source", "")).strip()
        if src:
            sources[src] += 1

        reach_val = r.get("reach")
        if reach_val and str(reach_val).strip().lower() not in ("n/a", "na", "-", "", "none", "pending"):
            try:
                total_reach += int(str(reach_val).replace(",", "").strip())
                reach_available += 1
            except (ValueError, TypeError):
                pass

    # Deduplicate press releases by source + first 5 words of headline
    pr_campaigns = set()
    interview_count = 0
    byline_count = 0
    for r in rows_data:
        src = str(r.get("source", "")).strip().lower()
        headline = str(r.get("headline", "")).strip()
        if src in ("press release", "pr", "media alert", "announcement"):
            pr_campaigns.add(normalise_name(headline))
        elif src in ("interview", "briefing", "media brief"):
            interview_count += 1
        elif src in ("byline", "op-ed", "opinion"):
            byline_count += 1

    english_count = sum(v for k, v in languages.items() if k.lower().startswith("eng"))
    arabic_count = sum(v for k, v in languages.items() if k.lower().startswith("arab"))
    tier1_count = sum(v for k, v in tiers.items() if "1" in str(k))
    tier2_count = sum(v for k, v in tiers.items() if "2" in str(k))

    top_publications = publications.most_common(5)

    return {
        "total_placements": total_placements,
        "english_count": english_count,
        "arabic_count": arabic_count,
        "tier1_count": tier1_count,
        "tier2_count": tier2_count,
        "print_count": sum(v for k, v in print_online.items() if "print" in k.lower()),
        "online_count": sum(v for k, v in print_online.items() if "online" in k.lower()),
        "media_type_breakdown": dict(media_types),
        "language_breakdown": dict(languages),
        "tier_breakdown": dict(tiers),
        "top_publications": top_publications,
        "unique_pr_campaigns": len(pr_campaigns),
        "interview_count": interview_count,
        "byline_count": byline_count,
        "total_reach": total_reach,
        "reach_available": reach_available,
        "source_breakdown": dict(sources),
        "rows": rows_data,
    }
