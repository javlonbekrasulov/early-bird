"""
This is what GitHub Actions runs once a day at your set time.

Pipeline:
1. Load sites.json
2. For each site: fetch posts, compare against last-seen date in SQLite
3. New posts --> summarize with Gemini
4. Build one Telegram digest message, grouped by site
5. Update last-seen date per site
6. Send the digest. Any site that fails to scrape gets its own
   separate error alert, but doesn't stop the other sites.
"""

import html
import json
from datetime import date

import db
import telegram
from scraper import fetch_posts
from summarizer import summarize_post


def load_sites(path: str = "sites.json") -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    db.init_db()
    sites = load_sites()

    digest_sections = []
    error_alerts = []     # separate messages for sites that failed

    for site in sites:
        name = site["name"]
        posts = fetch_posts(site)

        if not posts:
            error_alerts.append(
                f"⚠️ {name}: got 0 posts this run. The site's HTML "
                f"structure may have changed -- selectors in sites.json "
                f"might need updating."
            )
            continue

        last_seen = db.get_last_seen_date(name)

        if last_seen is None:
            newest = max(p["post_date"] for p in posts)
            db.update_last_seen_date(name, newest)
            print(f"[INFO] {name}: first run, baseline set to {newest}. "
                  f"No digest sent for this site today.")
            continue

        new_posts = [p for p in posts if p["post_date"] > last_seen]

        if new_posts:
            lines = [f"📌 From: {name}\n"]
            for post in new_posts:
                summary = summarize_post(post["title"])
                lines.append(f"- {html.escape(summary)} --> <a href=\"{post['link']}\">LINK</a>")
            digest_sections.append("\n".join(lines))

            newest = max(p["post_date"] for p in new_posts)
            db.update_last_seen_date(name, newest)
        else:
            print(f"[INFO] {name}: no new posts since {last_seen}.")

    # Send the digest if there's anything new. Otherwise still send a
    # short "nothing today" message
    if digest_sections:
        full_message = "🔔 New postings today:\n\n" + "\n\n".join(digest_sections)
        telegram.send_message(full_message)
    else:
        print("[INFO] No new posts across any site today.")
        telegram.send_message("No new posts across any site today.")

    # Send error alerts separately, so they don't get buried/lost
    # inside a normal digest
    for alert in error_alerts:
        telegram.send_message(alert)


if __name__ == "__main__":
    main()