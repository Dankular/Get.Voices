#!/usr/bin/env python3
"""Dump ElevenLabs Voice Library entries (name, description, preview_url).

Uses the official GET /v1/shared-voices endpoint. API key is read from the
ELEVENLABS_API_KEY environment variable (never hardcode it).

Examples:
  ELEVENLABS_API_KEY=... ./get_voices.py --use-case social_media -o voices.csv
  ./get_voices.py --search narrator --max 200 --format json -o narrators.json
"""
import argparse, csv, json, os, sys, time
import urllib.error, urllib.parse, urllib.request

URL = "https://api.elevenlabs.io/v1/shared-voices"
FIELDS = ["name", "description", "preview_url"]


def fetch_page(key, params, retries=4):
    req = urllib.request.Request(f"{URL}?{urllib.parse.urlencode(params)}",
                                 headers={"xi-api-key": key})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(2 ** (attempt + 1))
                continue
            raise SystemExit(f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")
        except urllib.error.URLError:
            if attempt < retries:
                time.sleep(2 ** (attempt + 1))
                continue
            raise


def iter_voices(key, filters, page_size, limit):
    page, n = 0, 0
    while True:
        data = fetch_page(key, {**filters, "page_size": page_size, "page": page})
        for v in data.get("voices", []):
            yield {f: v.get(f) for f in FIELDS}
            n += 1
            if limit and n >= limit:
                return
        if not data.get("has_more") or not data.get("voices"):
            return
        page += 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--use-case", help="e.g. social_media, narration, characters_animation, conversational")
    ap.add_argument("--category", help="e.g. professional, famous, high_quality")
    ap.add_argument("--language")
    ap.add_argument("--gender")
    ap.add_argument("--accent")
    ap.add_argument("--age")
    ap.add_argument("--search")
    ap.add_argument("--max", type=int, default=0, help="stop after N voices (0 = all)")
    ap.add_argument("--page-size", type=int, default=100)
    ap.add_argument("--format", choices=["csv", "json", "jsonl"], default="csv")
    ap.add_argument("-o", "--output", default="-")
    a = ap.parse_args()

    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        sys.exit("Set ELEVENLABS_API_KEY")
    filters = {k: v for k, v in {
        "use_cases": a.use_case, "category": a.category, "language": a.language,
        "gender": a.gender, "accent": a.accent, "age": a.age, "search": a.search,
    }.items() if v}

    out = sys.stdout if a.output == "-" else open(a.output, "w", newline="", encoding="utf-8")
    rows = iter_voices(key, filters, a.page_size, a.max)
    count = 0
    if a.format == "csv":
        w = csv.DictWriter(out, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r); count += 1
    elif a.format == "jsonl":
        for r in rows:
            out.write(json.dumps(r, ensure_ascii=False) + "\n"); count += 1
    else:
        lst = list(rows); count = len(lst)
        json.dump(lst, out, ensure_ascii=False, indent=2)
    if out is not sys.stdout:
        out.close()
    print(f"wrote {count} voices", file=sys.stderr)


if __name__ == "__main__":
    main()
