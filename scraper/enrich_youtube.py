"""Fast concurrent enricher for YouTube videos & shorts.
Fetches real upload dates (YYYY-MM-DD) and real like counts directly from watch pages.
Caches progress continuously so it can be resumed or run incrementally.
"""
import json
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
YT_ALL = ROOT / "src/data/youtube_all.json"
CACHE_FILE = ROOT / "src/data/yt_enrich_cache.json"

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
]


def fetch_single(vid):
    # Try watch page first, fallback to shorts page
    for url in [f"https://www.youtube.com/shorts/{vid}", f"https://www.youtube.com/watch?v={vid}"]:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENTS[0], "Accept-Language": "en-US,en;q=0.9"})
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode("utf-8", "ignore")
                date_m = (
                    re.search(r'itemprop="datePublished" content="([^"]+)"', html)
                    or re.search(r'"publishDate":"([^"]+)"', html)
                    or re.search(r'"uploadDate":"([^"]+)"', html)
                )
                like_m = (
                    re.search(r'"likeCount":"(\d+)"', html)
                    or re.search(r'"accessibilityText":"([\d,]+)\s*likes?"', html, re.I)
                    or re.search(r'"label":"([\d,]+)\s*likes?"', html, re.I)
                )

                date_str = date_m.group(1)[:10] if date_m else ""
                likes = int(like_m.group(1).replace(",", "")) if like_m else 0

                if date_str:
                    return vid, {"date": date_str, "likes": likes}
        except Exception:
            continue
    return vid, {"date": "", "likes": 0}



def enrich_all(max_workers=25):
    if not YT_ALL.exists():
        print("No youtube_all.json found!")
        return

    items = json.loads(YT_ALL.read_text(encoding="utf-8"))
    cache = {}
    if CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    to_fetch = [item["id"] for item in items if item["id"] not in cache or not cache[item["id"]].get("date")]
    print(f"Total items: {len(items)} | Already in cache: {len(cache)} | To fetch: {len(to_fetch)}")

    if to_fetch:
        count = 0
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_id = {executor.submit(fetch_single, vid): vid for vid in to_fetch}
            for future in as_completed(future_to_id):
                vid, meta = future.result()
                cache[vid] = meta
                count += 1
                if count % 50 == 0 or count == len(to_fetch):
                    CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
                    elapsed = time.time() - t0
                    rate = count / elapsed if elapsed > 0 else 0
                    print(f"Progress: {count}/{len(to_fetch)} fetched ({rate:.1f} items/sec)")

    # Update youtube_all.json with enriched dates and likes
    updated_count = 0
    for item in items:
        vid = item["id"]
        if vid in cache:
            if cache[vid].get("date"):
                item["upload_date"] = cache[vid]["date"]
            if cache[vid].get("likes") is not None:
                item["likes"] = cache[vid]["likes"]
            updated_count += 1

    YT_ALL.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Successfully enriched {updated_count} items in {YT_ALL.relative_to(ROOT)}")


if __name__ == "__main__":
    enrich_all()
