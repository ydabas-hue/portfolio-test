"""One-time seed scrape -> src/data/social.json + src/assets/social/*.jpg.

Run from the repo root:  scraper/.venv/bin/python scraper/scrape.py
Public pages only, logged out, no credentials. Re-running keeps `featured` flags.
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from scrapling.fetchers import Fetcher

import parse

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "src/data/social.json"
THUMBS = ROOT / "src/assets/social"
OVERRIDE = ROOT / "scraper/instagram_posts.txt"
IG_ACCOUNTS = ["abhishekpandey_26", "spinandswing26"]
IG_REELS_ACCOUNTS = ["abhishekpandey_26"]  # Pulse of the Crowd: reels from this account only
YT_CHANNELS = ["spinandswing26", "abhishekunseen26"]
LINKEDIN = "abhishek-pandey-26sep03"


def get(url, **kw):
    time.sleep(2)  # ponytail: fixed politeness delay; ~50 requests total, no need for a rate limiter
    page = Fetcher.get(url, impersonate="chrome", stealthy_headers=True, timeout=30, **kw)
    if page.status != 200:
        raise RuntimeError(f"HTTP {page.status} for {url}")
    return page


def post_json(url, body, **kw):
    time.sleep(2)  # ponytail: same politeness delay as get()
    page = Fetcher.post(url, data=json.dumps(body), headers={"Content-Type": "application/json"},
                         impersonate="chrome", stealthy_headers=True, timeout=30, **kw)
    if page.status != 200:
        raise RuntimeError(f"HTTP {page.status} for {url}")
    return page


def meta(page, prop):
    return page.css(f'meta[property="{prop}"]::attr(content)').get()


def save_image(url, name):
    (THUMBS / name).write_bytes(get(url).body)
    return name


def profile_row(platform, handle, url):
    return {"platform": platform, "handle": handle, "url": url,
            "followers": None, "postCount": None, "name": None, "headline": None}


def scrape_instagram(featured, pool_size=6):
    """Ranks by real view count from IG_REELS_ACCOUNTS's own /reels/ tab, not upload recency.

    Neither the profile grid nor an individual reel's own page exposes any view/play
    count when logged out -- checked live, only like_count and comment_count exist
    there. The dedicated /reels/ tab is different: its server-embedded GraphQL
    connection carries an exact play_count, like_count, shortcode and thumbnail URL for
    every reel already, no per-reel fetch needed to rank them. Confirmed live:
    abhishekpandey_26's /reels/ tab surfaces reels the profile grid's 12 most recent
    items never show at all -- the two are genuinely different pools.
    """
    def fetch_override_post(c):
        kind = "reel" if c["isReel"] else "p"
        url = f"https://www.instagram.com/{kind}/{c['shortcode']}/"
        page = get(url)
        image = meta(page, "og:image")
        if not image:
            raise RuntimeError(f"no og:image for {url}")
        info = parse.parse_instagram_post(meta(page, "og:description"))
        thumb = save_image(image, f"ig-{c['shortcode']}.jpg")
        return {"platform": "instagram", "account": info["account"] or "unknown",
                "shortcode": c["shortcode"], "url": url, "caption": info["caption"],
                "likes": info["likes"], "views": None, "isReel": c["isReel"], "thumb": thumb,
                "featured": c["shortcode"] in featured}

    profiles = []
    for handle in IG_ACCOUNTS:
        row = profile_row("instagram", handle, f"https://www.instagram.com/{handle}/")
        try:
            row.update(parse.parse_instagram_profile(meta(get(row["url"]), "og:description")))
        except Exception as err:
            print("WARN IG profile", err)
        profiles.append(row)

    posts = []
    if OVERRIDE.exists():
        urls = [line.strip() for line in OVERRIDE.read_text().splitlines() if line.strip()]
        for c in filter(None, map(parse.parse_instagram_post_url, urls)):
            try:
                posts.append(fetch_override_post(c))
            except Exception as err:
                print("WARN IG post", err)
        return profiles, posts

    for handle in IG_REELS_ACCOUNTS:
        try:
            reels_page = get(f"https://www.instagram.com/{handle}/reels/")
            candidates = parse.parse_instagram_reels_tab(reels_page.body.decode("utf-8", "ignore"))
        except Exception as err:
            print("WARN IG reels tab", err)
            candidates = []
        candidates.sort(key=lambda c: c["views"], reverse=True)
        for c in candidates[:pool_size]:
            url = f"https://www.instagram.com/reel/{c['id']}/"
            try:
                caption = parse.parse_instagram_post(meta(get(url), "og:description"))["caption"]
                thumb = save_image(c["thumbUrl"], f"ig-{c['id']}.jpg")
            except Exception as err:
                print("WARN IG reel", err)
                continue
            posts.append({"platform": "instagram", "account": handle, "shortcode": c["id"],
                          "url": url, "caption": caption, "likes": c["likes"], "views": c["views"],
                          "isReel": True, "thumb": thumb, "featured": c["id"] in featured})

    # A reel cross-posted to both accounts shows up in both accounts' own /reels/ tab --
    # keep it once rather than showing the same card twice.
    posts = list({p["shortcode"]: p for p in posts}.values())
    return profiles, posts


def youtube_thumb(video_id):
    for size in ("maxresdefault", "hqdefault"):
        try:
            return save_image(f"https://i.ytimg.com/vi/{video_id}/{size}.jpg", f"yt-{video_id}.jpg")
        except Exception:
            continue
    return None


def scrape_youtube(featured, pool_size=8):
    """Ranks by real view count, not upload recency.

    The RSS feed used here previously only ever returns a channel's ~15 most recent
    uploads, so an older video with far more views than anything recent was structurally
    invisible to it -- not a parsing bug, a coverage gap. Fixed by reading the channel's
    /videos AND /shorts listings instead (both render an approximate view count per item
    already), sorting the combined pool ourselves (YouTube's own "?sort=p" no longer sorts
    anything server-side on the current /videos page -- verified live), and then fetching
    each of the top candidates' own watch page for its exact view count and publish date.

    Shorts turned out to matter a lot more than the plain /shorts tab shows: it renders
    "Latest" order by default, capped at recent uploads' modest view counts (spinandswing26
    tops out around 235K there). Its "Popular" sort is a client-side action -- clicking the
    chip POSTs a continuation token to /youtubei/v1/browse -- but that token already exists
    in the page's own initial render, so this replicates the click as a direct request rather
    than needing a real browser. Confirmed live: this surfaces an 18M-view Short on the same
    channel that neither /videos nor the plain /shorts page has any way to find.
    """
    profiles, videos = [], []
    for handle in YT_CHANNELS:
        url = f"https://www.youtube.com/@{handle}"
        row = profile_row("youtube", handle, url)
        try:
            page = get(url, headers={"Accept-Language": "en-US,en;q=0.9"})
            info = parse.parse_youtube_channel(page.body.decode("utf-8", "ignore"), handle)
            row["followers"] = info["followers"]
            if not info["channelId"]:
                raise RuntimeError(f"no channel id on {url}")
            listing = get(f"https://www.youtube.com/channel/{info['channelId']}/videos")
            shorts_page = get(f"https://www.youtube.com/channel/{info['channelId']}/shorts")
            shorts_html = shorts_page.body.decode("utf-8", "ignore")
            shorts_candidates = parse.parse_youtube_shorts_page(shorts_html)  # fallback: recency order
            req = parse.parse_youtube_shorts_popular_request(shorts_html)
            if req:
                try:
                    popular = post_json(
                        f"https://www.youtube.com/youtubei/v1/browse?prettyPrint=false&key={req['apiKey']}",
                        {"context": {"client": {"clientName": "WEB", "clientVersion": req["clientVersion"]}},
                         "continuation": req["token"]},
                    )
                    shorts_candidates = parse.parse_youtube_shorts_page(popular.body.decode("utf-8", "ignore"))
                except Exception as err:
                    print("WARN YT shorts-popular, falling back to /shorts recency order:", err)
            candidates = {v["id"]: v for v in (
                parse.parse_youtube_videos_page(listing.body.decode("utf-8", "ignore")) + shorts_candidates
            )}.values()
            candidates = sorted(candidates, key=lambda v: v["views"] or 0, reverse=True)
            for c in candidates[:pool_size]:
                try:
                    watch = get(f"https://www.youtube.com/watch?v={c['id']}")
                    detail = parse.parse_youtube_watch_page(watch.body.decode("utf-8", "ignore"))
                    thumb = youtube_thumb(c["id"])
                    if not thumb or detail["views"] is None:
                        raise RuntimeError(f"incomplete detail for {c['id']}: {detail}, thumb={thumb}")
                    videos.append({"platform": "youtube", "channel": handle, "id": c["id"],
                                   "title": detail["title"], "publishedAt": detail["publishedAt"],
                                   "views": detail["views"], "thumb": thumb,
                                   "featured": c["id"] in featured})
                except Exception as err:
                    print("WARN YT video", err)
        except Exception as err:
            print("WARN YT", err)
        profiles.append(row)
    return profiles, videos


def scrape_linkedin():
    url = f"https://www.linkedin.com/in/{LINKEDIN}"
    row = profile_row("linkedin", LINKEDIN, url)
    try:
        row.update(parse.parse_linkedin(meta(get(url), "og:title")))
    except Exception as err:
        print("WARN LinkedIn", err, "- LinkedIn falls back to a plain link")
    return row


def check_not_wiped(previous, videos, posts):
    """A scrape can come back empty without raising -- e.g. every watch-page fetch
    silently returns a bot-check/consent page instead of real content (seen live
    from a GitHub Actions runner IP, not reproducible from a normal machine).
    Refuse to overwrite real data with nothing rather than wiping it.
    """
    if not videos and previous.get("videos"):
        raise RuntimeError(f"scrape_youtube returned 0 videos but {len(previous['videos'])} existed before -- refusing to overwrite")
    if not posts and previous.get("posts"):
        raise RuntimeError(f"scrape_instagram returned 0 posts but {len(previous['posts'])} existed before -- refusing to overwrite")


def main():
    THUMBS.mkdir(parents=True, exist_ok=True)
    previous = json.loads(OUT_JSON.read_text()) if OUT_JSON.exists() else {}
    featured = {r["id"] for r in previous.get("videos", []) if r.get("featured")} | \
               {r["shortcode"] for r in previous.get("posts", []) if r.get("featured")}

    ig_profiles, posts = scrape_instagram(featured)
    yt_profiles, videos = scrape_youtube(featured)
    check_not_wiped(previous, videos, posts)

    data = {
        "scrapedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "profiles": ig_profiles + yt_profiles + [scrape_linkedin()],
        "videos": videos,
        "posts": posts,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"profiles={len(data['profiles'])} videos={len(videos)} posts={len(posts)} -> {OUT_JSON.relative_to(ROOT)}")

    # Automatically refresh semantic database and export CSV + JSON
    try:
        import semantic_db
        semantic_db.generate_semantic_database()
    except Exception as err:
        print("WARN: semantic database generation failed:", err)


if __name__ == "__main__":
    main()

