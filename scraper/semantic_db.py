"""Semantic Database Generator for Abhishek Pandey's Cricket Content & Social Media.

Generates:
1. src/data/media_database.csv
2. public/media_database.csv (accessible via live site at /media_database.csv)
3. src/data/media_database.json
4. public/media_database.json

Categorizes every video, short, reel, and post semantically with:
- Tournament (DPL 2026, IPL 2026, IPL 2025, WPL 2026, T20 World Cup, etc.)
- Accreditation Status (Accredited Field-of-Play, Independent, Partner, Studio)
- Content Format (Story Behind the Post, Fan Vox Pop, Cricket Trivia, Match Analysis, etc.)
- Featured Entities (Teams, Players, Franchises)
- View counts, like counts, direct clickable URLs, and publish dates.
"""
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOCIAL_JSON = ROOT / "src/data/social.json"
PAVILION_ASTRO = ROOT / "src/components/Pavilion.astro"

SRC_CSV = ROOT / "src/data/media_database.csv"
PUB_CSV = ROOT / "public/media_database.csv"
SRC_JSON = ROOT / "src/data/media_database.json"
PUB_JSON = ROOT / "public/media_database.json"

# Known curated metadata mappings for career innings and landmark content
KNOWN_METADATA = {
    # DPL 2026 (Field-of-play accredited media)
    "DcRzXB-zlPg": {
        "tournament": "DPL 2026 (Delhi Premier League)",
        "accreditation": "Accredited (DPL Field-of-Play Media Pass)",
        "format": "Boundary Rope Story & Celebration",
        "entities": "Delhi Premier League (DPL)",
        "year": "2026",
    },
    "DcOV2DtBXIL": {
        "tournament": "DPL 2026 (Delhi Premier League)",
        "accreditation": "Accredited (DPL Field-of-Play Media Pass)",
        "format": "Story Behind the Post (Player Interview)",
        "entities": "Vansh Bedi, Central Delhi Kings",
        "year": "2026",
    },
    "DcdlCohB4qZ": {
        "tournament": "DPL 2026 (Delhi Premier League)",
        "accreditation": "Accredited (DPL Field-of-Play Media Pass)",
        "format": "Story Behind the Post (Player Interview)",
        "entities": "Himmat Singh, Delhi Premier League (DPL)",
        "year": "2026",
    },
    "DclYxOiBsuy": {
        "tournament": "DPL 2026 (Delhi Premier League)",
        "accreditation": "Accredited (DPL Field-of-Play Media Pass)",
        "format": "Story Behind the Post (Player Interview)",
        "entities": "Anuj Rawat, Purani Dilli, Gujarat Titans (GT)",
        "year": "2026",
    },
    "Dc2Rv1shQzz": {
        "tournament": "DPL 2026 (Delhi Premier League)",
        "accreditation": "Accredited (DPL Field-of-Play Media Pass)",
        "format": "Story Behind the Post (Player Interview)",
        "entities": "Priya Punia, South Delhi Superstarz",
        "year": "2026",
    },
    "Dcs1bhEoeTf": {
        "tournament": "DPL 2026 (Delhi Premier League)",
        "accreditation": "Accredited (DPL Field-of-Play Media Pass)",
        "format": "Matchday Highlights & Captain Profile",
        "entities": "Tejasvi Dahiya, South Delhi Superstarz",
        "year": "2026",
    },
    "Dc2YOiqhiDb": {
        "tournament": "DPL 2026 (Delhi Premier League)",
        "accreditation": "Accredited (DPL Field-of-Play Media Pass)",
        "format": "Story Behind the Post (Player Interview)",
        "entities": "Shweta Sehrawat, South Delhi Superstarz",
        "year": "2026",
    },

    # IPL 2026
    "DW84LM4y4Fr": {
        "tournament": "IPL 2026",
        "accreditation": "Independent Fan Coverage",
        "format": "Viral Stadium Moment & Banter",
        "entities": "Gujarat Titans (GT)",
        "year": "2026",
    },
    "DY8twCQohkY": {
        "tournament": "IPL 2026",
        "accreditation": "Independent Fan Coverage",
        "format": "Stadium Vlog & Fan Reaction",
        "entities": "Gujarat Titans (GT)",
        "year": "2026",
    },
    "DYQOCiysdD0": {
        "tournament": "IPL 2026",
        "accreditation": "Independent Fan Coverage",
        "format": "Match Reaction & Points Table",
        "entities": "Gujarat Titans (GT)",
        "year": "2026",
    },
    "DY8nQzKhspB": {
        "tournament": "IPL 2026",
        "accreditation": "Independent Fan Coverage",
        "format": "Stadium Fan Vlog",
        "entities": "IPL Final",
        "year": "2026",
    },
    "DY7rG2Jhmdh": {
        "tournament": "IPL 2026",
        "accreditation": "Independent Fan Coverage",
        "format": "Matchday Banter & Rivalry Vox Pop",
        "entities": "IPL Rivalry",
        "year": "2026",
    },

    # ICC Men's T20 World Cup 2026 / My11Circle
    "DUvn-h4kkCU": {
        "tournament": "ICC Men's T20 World Cup 2026",
        "accreditation": "Commercial Partner (My11Circle)",
        "format": "Fan Reaction & Banter",
        "entities": "India vs Pakistan",
        "year": "2026",
    },
    "DUyWIqjgQu7": {
        "tournament": "ICC Men's T20 World Cup 2026",
        "accreditation": "Commercial Partner (My11Circle)",
        "format": "Matchday Banter & Rivalry",
        "entities": "India vs Pakistan",
        "year": "2026",
    },
    "DVlsJKSjJTH": {
        "tournament": "ICC Men's T20 World Cup 2026",
        "accreditation": "Commercial Partner (My11Circle)",
        "format": "Tactical & Match Analysis",
        "entities": "Team India",
        "year": "2026",
    },
    "DVRDbLVCqmy": {
        "tournament": "ICC Men's T20 World Cup 2026",
        "accreditation": "Commercial Partner (My11Circle)",
        "format": "Tournament Analysis",
        "entities": "Australia, Super 8",
        "year": "2026",
    },
    "DVv1RPMkl4T": {
        "tournament": "ICC Men's T20 World Cup 2026",
        "accreditation": "Commercial Partner (My11Circle)",
        "format": "Player Performance Review",
        "entities": "Sanju Samson, Team India",
        "year": "2026",
    },

    # WPL 2026
    "DT2m9vACEU8": {
        "tournament": "WPL 2026",
        "accreditation": "Independent Fan Coverage",
        "format": "Fan Vox Pop & Reaction",
        "entities": "Harmanpreet Kaur, WPL",
        "year": "2026",
    },
    "DT8FW8_iAc5": {
        "tournament": "WPL 2026",
        "accreditation": "Independent Fan Coverage",
        "format": "Fan Vox Pop & Reaction",
        "entities": "WPL Fan Community",
        "year": "2026",
    },
    "DUINPzWkrlj": {
        "tournament": "WPL 2026",
        "accreditation": "Independent Fan Coverage",
        "format": "Cricket Trivia & Vox Pop",
        "entities": "WPL",
        "year": "2026",
    },
    "DULh2v2jcsm": {
        "tournament": "WPL 2026",
        "accreditation": "Independent Fan Coverage",
        "format": "Cricket Trivia & Fan Quiz",
        "entities": "Royal Challengers Bengaluru (RCB)",
        "year": "2026",
    },
    "DUSSdE6EhS8": {
        "tournament": "WPL 2026",
        "accreditation": "Independent Fan Coverage",
        "format": "Cricket Trivia & Fan Quiz",
        "entities": "Royal Challengers Bengaluru (RCB)",
        "year": "2026",
    },

    # IPL 2025
    "DJUtWygz-T2": {
        "tournament": "IPL 2025",
        "accreditation": "Independent Fan Coverage",
        "format": "Stadium Vlog & Fan Reaction",
        "entities": "Gujarat Titans (GT), Mumbai Indians (MI)",
        "year": "2025",
    },
    "DJTjMYSSL4B": {
        "tournament": "IPL 2025",
        "accreditation": "Independent Fan Coverage",
        "format": "Cricket Trivia & Player Guessing",
        "entities": "Royal Challengers Bengaluru (RCB)",
        "year": "2025",
    },
    "DJmHLxRSeFU": {
        "tournament": "IPL 2025",
        "accreditation": "Independent Fan Coverage",
        "format": "Cricket Trivia & Player Guessing",
        "entities": "Sunrisers Hyderabad (SRH)",
        "year": "2025",
    },
    "DKMMtRnIzAE": {
        "tournament": "IPL 2025",
        "accreditation": "Independent Fan Coverage",
        "format": "Cricket Trivia & Player Guessing",
        "entities": "Royal Challengers Bengaluru (RCB)",
        "year": "2025",
    },
    "DKOxcw4y6LX": {
        "tournament": "IPL 2025",
        "accreditation": "Independent Fan Coverage",
        "format": "Cricket Trivia & Player Guessing",
        "entities": "Mumbai Indians (MI), Gujarat Titans (GT)",
        "year": "2025",
    },

    # YouTube Highlights
    "DxgBGpUzZ08": {
        "tournament": "IPL 2026",
        "accreditation": "Independent Fan Coverage",
        "format": "Fan Vox Pop & Banter",
        "entities": "Gujarat Titans (GT), Mumbai Indians (MI)",
        "year": "2026",
    },
    "YPeQi6-h30M": {
        "tournament": "General Cricket Series",
        "accreditation": "Creator Studio / Digital",
        "format": "Cricket Trivia & Jersey Guessing",
        "entities": "Indian Cricket Team",
        "year": "2026",
    },
    "5XcoId1xQfI": {
        "tournament": "General Cricket Series",
        "accreditation": "Creator Studio / Digital",
        "format": "Cricket Trivia & Player Guessing",
        "entities": "Spin & Swing",
        "year": "2025",
    },
    "ehA4CLVExQM": {
        "tournament": "General Cricket Series",
        "accreditation": "Creator Studio / Digital",
        "format": "Cricket Trivia & Jersey Guessing",
        "entities": "Indian Cricket Team",
        "year": "2026",
    },
    "O0ILNSPGcsM": {
        "tournament": "ICC Men's T20 World Cup 2026",
        "accreditation": "Creator Studio / Digital",
        "format": "Squad Trivia & Quiz",
        "entities": "Team India",
        "year": "2026",
    },
    "kaCk8jJC1Rk": {
        "tournament": "IPL 2026",
        "accreditation": "Creator Studio / Digital",
        "format": "Squad Trivia & Quiz",
        "entities": "Gujarat Titans (GT)",
        "year": "2026",
    },
    "R0V4qcXudOk": {
        "tournament": "General Cricket Series",
        "accreditation": "Creator Studio / Digital",
        "format": "Cricket Trivia & Jersey Guessing",
        "entities": "Indian Cricket Team",
        "year": "2026",
    },
    "GIJrFq2RTgE": {
        "tournament": "IPL 2026",
        "accreditation": "Creator Studio / Digital",
        "format": "Squad Trivia & Quiz",
        "entities": "Royal Challengers Bengaluru (RCB)",
        "year": "2026",
    },
}


def classify_text(text, channel_or_account, published_at=""):
    """Heuristic rule classifier for unmapped or newly scraped content."""
    text_lower = (text or "").lower()
    year = ""
    if published_at:
        try:
            year = published_at.split("-")[0]
        except Exception:
            year = "2026"
    else:
        year = "2026"

    # 1. Determine Tournament
    if "dpl" in text_lower or "delhi premier league" in text_lower or "purani dilli" in text_lower or "southdelhisuperstarz" in text_lower:
        tournament = f"DPL {year or '2026'} (Delhi Premier League)"
    elif "wpl" in text_lower or "women" in text_lower or "harmanpreet" in text_lower:
        tournament = f"WPL {year or '2026'}"
    elif "t20 world cup" in text_lower or "world cup" in text_lower or "india vs pak" in text_lower:
        tournament = f"ICC Men's T20 World Cup {year or '2026'}"
    elif any(team in text_lower for team in ["ipl", "gt", "rcb", "csk", "mi", "srh", "kkr", "rajasthan royals", "gujarat titans", "mumbai indians"]):
        tournament = f"IPL {year or '2026'}"
    elif channel_or_account == "abhishekunseen26" or "vlog" in text_lower or "scooty" in text_lower or "gaming zone" in text_lower:
        tournament = "N/A (Personal / Creator Journey)"
    elif "guess the" in text_lower or "trivia" in text_lower or "jersey" in text_lower:
        tournament = "General Cricket Trivia Series"
    else:
        tournament = "Cricket Coverage & Commentary"

    # 2. Determine Accreditation Status
    if "dpl" in text_lower and ("episode" in text_lower or "story behind" in text_lower or "celebration" in text_lower or "captain" in text_lower):
        accreditation = "Accredited (DPL Field-of-Play Media Pass)"
    elif "my11circle" in text_lower:
        accreditation = "Commercial Partner (My11Circle)"
    elif channel_or_account == "abhishekunseen26":
        accreditation = "Creator Studio / Personal"
    elif "guess the" in text_lower or "jersey" in text_lower or "trivia" in text_lower:
        accreditation = "Creator Studio / Digital Production"
    else:
        accreditation = "Independent Fan Coverage"

    # 3. Determine Format
    if "story behind the post" in text_lower or ("episode" in text_lower and "ft" in text_lower):
        fmt = "Story Behind the Post (Player Interview)"
    elif "vox pop" in text_lower or "fan" in text_lower or "reaction" in text_lower:
        fmt = "Fan Vox Pop & Stadium Reaction"
    elif "guess the player" in text_lower:
        fmt = "Cricket Trivia & Player Guessing"
    elif "guess the jersey" in text_lower or "jersey number" in text_lower:
        fmt = "Cricket Trivia & Jersey Guessing"
    elif "guess the squad" in text_lower or "squad" in text_lower:
        fmt = "Cricket Trivia & Squad Quiz"
    elif "vlog" in text_lower:
        fmt = "Behind The Scenes / Vlog"
    elif "analysis" in text_lower or "breakdown" in text_lower:
        fmt = "Match Analysis & Tactics"
    else:
        fmt = "Short-form Cricket Content"

    # 4. Extract Entities
    entities = []
    entity_map = {
        "gt": "Gujarat Titans (GT)",
        "gujarat titans": "Gujarat Titans (GT)",
        "mi": "Mumbai Indians (MI)",
        "mumbai indians": "Mumbai Indians (MI)",
        "rcb": "Royal Challengers Bengaluru (RCB)",
        "srh": "Sunrisers Hyderabad (SRH)",
        "anuj rawat": "Anuj Rawat",
        "anujrawat": "Anuj Rawat",
        "vansh bedi": "Vansh Bedi",
        "vanshbedi": "Vansh Bedi",
        "priya punia": "Priya Punia",
        "priyapunia": "Priya Punia",
        "shweta sehrawat": "Shweta Sehrawat",
        "shwetasehrawat": "Shweta Sehrawat",
        "himmat singh": "Himmat Singh",
        "himmatsingh": "Himmat Singh",
        "tejasvi dhaiya": "Tejasvi Dahiya",
        "tejasvidhaiya": "Tejasvi Dahiya",
        "harmanpreet": "Harmanpreet Kaur",
        "sanju": "Sanju Samson",
        "south delhi": "South Delhi Superstarz",
        "southdelhisuperstarz": "South Delhi Superstarz",
        "purani dilli": "Purani Dilli",
        "puranidilli": "Purani Dilli",
        "central delhi": "Central Delhi Kings",
        "centraldelhikings": "Central Delhi Kings",
    }
    for k, v in entity_map.items():
        if k in text_lower and v not in entities:
            entities.append(v)
    if not entities:
        entities_str = "Spin & Swing" if channel_or_account == "spinandswing26" else "Abhishek Unseen"
    else:
        entities_str = ", ".join(entities)

    return {
        "tournament": tournament,
        "accreditation": accreditation,
        "format": fmt,
        "entities": entities_str,
        "year": year,
    }


def parse_pavilion_reels():
    """Extract curated career innings reels from Pavilion.astro."""
    if not PAVILION_ASTRO.exists():
        return []
    text = PAVILION_ASTRO.read_text(encoding="utf-8")
    blocks = re.findall(
        r"dates:\s*['\"]([^'\"]+)['\"],\s*title:\s*['\"]([^'\"]+)['\"],\s*accredited:\s*(true|false).*?reels:\s*\[(.*?)\]\s*\}",
        text,
        re.S,
    )
    items = []
    for dates, tourney_title, accred_bool, reels_block in blocks:
        reels = re.findall(
            r"id:\s*['\"]([^'\"]+)['\"],\s*url:\s*['\"]([^'\"]+)['\"].*?views:\s*(\d+),\s*likes:\s*(\d+),\s*caption:\s*['\"]([^'\"]+)['\"]",
            reels_block,
            re.S,
        )
        for rid, rurl, rviews, rlikes, rcap in reels:
            items.append({
                "platform": "Instagram",
                "handle": "@abhishekpandey_26",
                "content_type": "Reel",
                "id": rid,
                "url": rurl.split("?")[0],  # clean canonical URL
                "title_caption": rcap,
                "views": int(rviews),
                "likes": int(rlikes),
                "upload_date": dates,
                "source": "Pavilion Timeline",
                "featured": True,
            })
    return items


def generate_semantic_database():
    """Build the consolidated semantic database and export to CSV + JSON."""
    social = {}
    if SOCIAL_JSON.exists():
        try:
            social = json.loads(SOCIAL_JSON.read_text(encoding="utf-8"))
        except Exception as e:
            print("WARN: could not read social.json:", e)

    items_by_id = {}

    # 1. Process YouTube videos & shorts from social.json
    for v in social.get("videos", []):
        vid = v["id"]
        channel = v.get("channel", "spinandswing26")
        title = v.get("title", "")
        pub_at = v.get("publishedAt", "")
        views = v.get("views", 0)
        likes = v.get("likes", None)
        featured = v.get("featured", False)
        url = f"https://www.youtube.com/watch?v={vid}"

        # Classify as Short or Long Video
        # In YouTube channels, shorts have titles with #shorts or are under shorts shelf
        is_short = "#short" in title.lower() or views > 500000 or channel == "abhishekunseen26" and views < 1000
        content_type = "Short" if is_short else "Video"

        items_by_id[vid] = {
            "platform": "YouTube",
            "handle": f"@{channel}",
            "content_type": content_type,
            "id": vid,
            "url": url,
            "title_caption": title,
            "views": views or 0,
            "likes": likes or 0,
            "upload_date": pub_at[:10] if pub_at else "",
            "source": "YouTube Scrape",
            "featured": featured,
        }

    # 2. Process Instagram posts & reels from social.json
    for p in social.get("posts", []):
        sid = p.get("shortcode")
        account = p.get("account", "abhishekpandey_26")
        caption = p.get("caption", "").strip()
        views = p.get("views", 0)
        likes = p.get("likes", 0)
        featured = p.get("featured", False)
        is_reel = p.get("isReel", True)
        url = p.get("url") or f"https://www.instagram.com/reel/{sid}/"

        # clean caption
        clean_cap = " ".join(caption.splitlines()).strip()
        clean_cap = re.sub(r"\s+", " ", clean_cap)

        items_by_id[sid] = {
            "platform": "Instagram",
            "handle": f"@{account}",
            "content_type": "Reel" if is_reel else "Post",
            "id": sid,
            "url": url.split("?")[0],
            "title_caption": clean_cap[:180],
            "views": views or 0,
            "likes": likes or 0,
            "upload_date": "",
            "source": "Instagram Scrape",
            "featured": featured,
        }

    # 3. Process Curated Pavilion Innings Timeline Reels
    for r in parse_pavilion_reels():
        rid = r["id"]
        if rid in items_by_id:
            # Update views/likes if curated has more complete info, or preserve latest scrape
            if not items_by_id[rid]["views"] and r["views"]:
                items_by_id[rid]["views"] = r["views"]
            if not items_by_id[rid]["likes"] and r["likes"]:
                items_by_id[rid]["likes"] = r["likes"]
            items_by_id[rid]["featured"] = True
            if not items_by_id[rid]["upload_date"]:
                items_by_id[rid]["upload_date"] = r["upload_date"]
        else:
            items_by_id[rid] = r

    # 4. Enrich every item with Semantic Analysis
    records = []
    for item_id, item in items_by_id.items():
        # Check known dictionary first
        known = KNOWN_METADATA.get(item_id)
        if known:
            tournament = known["tournament"]
            accreditation = known["accreditation"]
            fmt = known["format"]
            entities = known["entities"]
            if not item["upload_date"] and known.get("year"):
                item["upload_date"] = f"{known['year']}-01-01"
        else:
            classified = classify_text(item["title_caption"], item["handle"].replace("@", ""), item["upload_date"])
            tournament = classified["tournament"]
            accreditation = classified["accreditation"]
            fmt = classified["format"]
            entities = classified["entities"]

        records.append({
            "Platform": item["platform"],
            "Handle": item["handle"],
            "Content_Type": item["content_type"],
            "Title_Caption": item["title_caption"],
            "URL": item["url"],
            "Content_ID": item["id"],
            "Upload_Date": item["upload_date"],
            "Views": item["views"],
            "Likes": item["likes"],
            "Tournament": tournament,
            "Accreditation_Status": accreditation,
            "Content_Format": fmt,
            "Featured_Entities": entities,
            "Featured_On_Portfolio": "Yes" if item["featured"] else "No",
        })

    # Sort descending by views
    records.sort(key=lambda x: int(x["Views"] or 0), reverse=True)

    # 5. Write CSV to src/data/media_database.csv and public/media_database.csv
    fieldnames = [
        "Platform",
        "Handle",
        "Content_Type",
        "Title_Caption",
        "URL",
        "Content_ID",
        "Upload_Date",
        "Views",
        "Likes",
        "Tournament",
        "Accreditation_Status",
        "Content_Format",
        "Featured_Entities",
        "Featured_On_Portfolio",
    ]

    for csv_path in [SRC_CSV, PUB_CSV]:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in records:
                writer.writerow(r)

    # 6. Write JSON metadata companion
    summary = {
        "updatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "totalItems": len(records),
        "totalViews": sum(int(r["Views"] or 0) for r in records),
        "totalLikes": sum(int(r["Likes"] or 0) for r in records),
        "platforms": list({r["Platform"] for r in records}),
        "handles": list({r["Handle"] for r in records}),
        "tournaments": list({r["Tournament"] for r in records}),
        "accreditations": list({r["Accreditation_Status"] for r in records}),
        "items": records,
    }
    for json_path in [SRC_JSON, PUB_JSON]:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"✅ Generated Media Database:")
    print(f"   - CSV:  {SRC_CSV.relative_to(ROOT)} & {PUB_CSV.relative_to(ROOT)}")
    print(f"   - JSON: {SRC_JSON.relative_to(ROOT)} & {PUB_JSON.relative_to(ROOT)}")
    print(f"   - Total records: {len(records)}")
    print(f"   - Total tracked views: {summary['totalViews']:,}")
    print(f"   - Total tracked likes: {summary['totalLikes']:,}")
    return records


if __name__ == "__main__":
    generate_semantic_database()
