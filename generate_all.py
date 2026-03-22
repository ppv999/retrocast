#!/usr/bin/env python3
"""RetroCast batch generator — runs all 8 broadcast styles, outputs to web/audio/{date}/.

Key optimization: styles sharing a geo_prefix share one fetch_news() call.
  - India (doordarshan-90s, akashvani) -> 1 fetch
  - UK (bbc-tv, bbc) -> 1 fetch
  - US (us-network, npr) -> 1 fetch
  - Brazil (jornal, reporter-esso) -> 1 fetch
Total: 4 fetches instead of 8.
"""

import json
import os
import sys
from datetime import datetime, timezone

from retrocast import STYLES, fetch_news, generate_audio, generate_script, verify_news

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "web", "audio")
MANIFEST_PATH = os.path.join(AUDIO_DIR, "manifest.json")

# Group styles by geo_prefix to share fetch_news() calls
GEO_GROUPS: dict[str, list[str]] = {}
for key, style in STYLES.items():
    geo = style.get("geo_prefix", "")
    GEO_GROUPS.setdefault(geo, []).append(key)


def load_manifest() -> dict:
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH) as f:
            return json.load(f)
    return {"dates": {}, "styles": {}}


def save_manifest(manifest: dict):
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    date_dir = os.path.join(AUDIO_DIR, today)
    os.makedirs(date_dir, exist_ok=True)

    # Validate API keys
    missing = [k for k in ("FIRECRAWL_API_KEY", "OPENAI_API_KEY", "ELEVENLABS_API_KEY")
               if not os.environ.get(k)]
    if missing:
        print(f"ERROR: Missing API keys: {', '.join(missing)}")
        sys.exit(1)

    manifest = load_manifest()

    # Ensure top-level keys exist
    if "dates" not in manifest:
        manifest["dates"] = {}
    if "styles" not in manifest:
        manifest["styles"] = {}

    errors: list[str] = []
    generated_count = 0

    for geo, style_keys in GEO_GROUPS.items():
        # Check if all styles in this geo group are already done
        pending = [k for k in style_keys
                   if not os.path.exists(os.path.join(date_dir, f"{k}.mp3"))]
        if not pending:
            print(f"\n{'='*60}")
            print(f"Geo group '{geo or 'default'}' — all styles already generated, skipping fetch.")
            print(f"{'='*60}")
            generated_count += len(style_keys)
            continue

        # One fetch per geo group
        ref_key = style_keys[0]
        print(f"\n{'='*60}")
        print(f"Fetching news for geo group: {geo or 'default'} "
              f"(styles: {', '.join(style_keys)})")
        print(f"{'='*60}\n")

        try:
            news = fetch_news(ref_key, target_date=today)
        except Exception as e:
            print(f"ERROR fetching news for {geo}: {e}")
            errors.extend(style_keys)
            continue

        total = sum(len(v) for v in news.values())
        if total == 0:
            print(f"WARNING: No articles fetched for {geo}, skipping group.")
            errors.extend(style_keys)
            continue

        print(f"\nFetched {total} articles.\n")

        # Defer verification until we know at least one style needs generating
        verification = None
        verification_done = False

        for style_key in style_keys:
            style = STYLES[style_key]

            # Skip if already generated for this date
            audio_path = os.path.join(date_dir, f"{style_key}.mp3")
            if os.path.exists(audio_path):
                print(f"\n--- Skipping: {style['name']} ({style_key}) — "
                      f"already generated for {today} ---")
                generated_count += 1
                continue

            print(f"\n--- Generating: {style['name']} ({style_key}) ---\n")

            try:
                # Verify news once per geo group, only when first needed
                if not verification_done:
                    print("  Verifying news claims...")
                    try:
                        verification = verify_news(news, ref_key)
                    except Exception as e:
                        print(f"  WARNING: News verification failed: {e}")
                    verification_done = True

                # Save articles for agent context
                articles_path = os.path.join(date_dir, f"{style_key}_articles.json")
                with open(articles_path, "w") as f:
                    json.dump(news, f, indent=2)

                print("  Generating script...")
                script = generate_script(news, style_key, verification=verification)
                print(f"  Script: {len(script.split())} words")

                # Save script for agent context
                script_path = os.path.join(date_dir, f"{style_key}_script.txt")
                with open(script_path, "w") as f:
                    f.write(script)

                print("  Generating audio...")
                audio = generate_audio(script, style_key)

                out_path = os.path.join(date_dir, f"{style_key}.mp3")
                with open(out_path, "wb") as f:
                    f.write(audio)
                print(f"  Saved: {out_path} ({len(audio):,} bytes)")

                # Update manifest — styles metadata
                manifest["styles"][style_key] = {
                    "name": style["name"],
                    "era": style.get("era", ""),
                    "lang": style.get("lang", ""),
                    "region": style.get("region", ""),
                }

                # Update manifest — date entry
                if today not in manifest["dates"]:
                    manifest["dates"][today] = {
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "styles": [],
                    }
                if style_key not in manifest["dates"][today]["styles"]:
                    manifest["dates"][today]["styles"].append(style_key)

                generated_count += 1

            except Exception as e:
                print(f"  ERROR generating {style_key}: {e}")
                errors.append(style_key)

    # Write manifest
    save_manifest(manifest)
    print(f"\nManifest written to {MANIFEST_PATH}")

    # Summary
    print(f"\n{'='*60}")
    print(f"Done! {generated_count}/{len(STYLES)} styles generated for {today}.")
    if errors:
        print(f"Failed: {', '.join(errors)}")
    print(f"{'='*60}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
