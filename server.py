#!/usr/bin/env python3
"""RetroCast Flask server — serves the frontend and provides an API for on-demand generation."""

import hmac
import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from ipaddress import ip_address
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

load_dotenv()

from retrocast import STYLES, fetch_news, generate_audio, generate_script, verify_news

app = Flask(__name__, static_folder="web")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Storage layer: Replit Object Storage on Replit, local filesystem elsewhere
# ---------------------------------------------------------------------------

_ON_REPLIT = bool(os.environ.get("REPL_ID"))

if _ON_REPLIT:
    from replit.object_storage import Client as _ObjClient
    from replit.object_storage.errors import ObjectNotFoundError as _ObjNotFound
    _store = _ObjClient(bucket_id=os.environ.get("DEFAULT_OBJECT_STORAGE_BUCKET_ID"))

# Local fallback: keys are "audio/<rest>", stored under <project>/audio/<rest>
_LOCAL_AUDIO_DIR = os.path.join(BASE_DIR, "audio")


def _key_to_local_path(key: str) -> str:
    """Map an object-storage key to a local filesystem path."""
    relative = key[len("audio/"):] if key.startswith("audio/") else key
    return os.path.join(_LOCAL_AUDIO_DIR, relative)


def _storage_put(key: str, data):
    """Write bytes or string — object storage on Replit, local file otherwise."""
    if _ON_REPLIT:
        if isinstance(data, (bytes, bytearray)):
            _store.upload_from_bytes(key, data)
        else:
            _store.upload_from_text(key, data)
    else:
        path = _key_to_local_path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        mode = "wb" if isinstance(data, (bytes, bytearray)) else "w"
        with open(path, mode) as f:
            f.write(data)


def _storage_get(key: str):
    """Read as bytes — object storage on Replit, local file otherwise. Returns None if missing."""
    if _ON_REPLIT:
        try:
            return _store.download_as_bytes(key)
        except _ObjNotFound:
            return None
    else:
        path = _key_to_local_path(key)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return f.read()


def _storage_exists(key: str) -> bool:
    """Check existence — object storage on Replit, local file otherwise."""
    if _ON_REPLIT:
        return _store.exists(key)
    else:
        return os.path.exists(_key_to_local_path(key))


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _valid_date(date_str: str) -> bool:
    return bool(_DATE_RE.match(date_str))


# Per-style generation locks to prevent duplicate concurrent generation
_gen_locks: dict[str, threading.Lock] = {key: threading.Lock() for key in STYLES}

# Cache fetched news per geo_prefix per day to avoid redundant API calls
_news_cache: dict[str, dict] = {}
_news_cache_lock = threading.Lock()

# Lock for manifest.json load-modify-save to prevent concurrent clobbering
_manifest_lock = threading.Lock()

# Generation progress tracking: {style_key: "step description"}
_gen_progress: dict[str, str] = {}

# Generation error tracking: {style_key: "error message"}
_gen_errors: dict[str, str] = {}

# Rate limiter for agent session creation (per-IP, sliding window)
_agent_rate: dict[str, list[float]] = {}
_agent_rate_lock = threading.Lock()
_AGENT_RATE_LIMIT = 3       # max sessions per IP per window
_AGENT_RATE_WINDOW = 60.0   # window in seconds


def _agent_rate_ok(ip: str) -> bool:
    """Return True if the IP is within the agent session rate limit."""
    now = time.monotonic()
    with _agent_rate_lock:
        timestamps = _agent_rate.get(ip, [])
        timestamps = [t for t in timestamps if now - t < _AGENT_RATE_WINDOW]
        if len(timestamps) >= _AGENT_RATE_LIMIT:
            _agent_rate[ip] = timestamps
            return False
        timestamps.append(now)
        _agent_rate[ip] = timestamps
        return True


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _load_manifest() -> dict:
    data = _storage_get("audio/manifest.json")
    if data is not None:
        return json.loads(data)
    return {"dates": {}, "styles": {}}


def _save_manifest(manifest: dict):
    _storage_put("audio/manifest.json", json.dumps(manifest, indent=2))


def _get_news_cached(style_key: str) -> dict:
    """Fetch news for a style, caching by geo_prefix + date."""
    geo = STYLES[style_key].get("geo_prefix", "")
    today = _today_str()
    cache_key = f"{geo}:{today}"

    with _news_cache_lock:
        if cache_key in _news_cache:
            return _news_cache[cache_key]

    news = fetch_news(style_key, target_date=today)

    with _news_cache_lock:
        _news_cache[cache_key] = news

    return news


_verification_cache: dict[str, dict] = {}
_verification_cache_lock = threading.Lock()


def _get_verification_cached(news: dict, style_key: str) -> dict | None:
    """Run verify_news, caching by geo_prefix + date."""
    geo = STYLES[style_key].get("geo_prefix", "")
    cache_key = f"{geo}:{_today_str()}"

    with _verification_cache_lock:
        if cache_key in _verification_cache:
            return _verification_cache[cache_key]

    try:
        verification = verify_news(news, style_key)
    except Exception as e:
        print(f"[server] WARNING: News verification failed: {e}")
        return None

    with _verification_cache_lock:
        _verification_cache[cache_key] = verification

    return verification


def _generate_style(date_str: str, style_key: str):
    """Generate audio for a style on a given date. Runs in a background thread."""
    try:
        style = STYLES[style_key]

        audio_key = f"audio/{date_str}/{style_key}.mp3"
        if _storage_exists(audio_key):
            return  # Already exists

        print(f"[server] Generating {style_key} for {date_str}...")

        _gen_progress[style_key] = "Fetching today's news via Firecrawl"
        news = _get_news_cached(style_key)
        total = sum(len(v) for v in news.values())
        if total == 0:
            print(f"[server] WARNING: No articles fetched for {style_key}")
            _gen_progress.pop(style_key, None)
            _gen_errors[style_key] = "No news articles found"
            return

        # Save articles for agent context
        _storage_put(f"audio/{date_str}/{style_key}_articles.json", json.dumps(news, indent=2))

        # Verify news claims (Fake News Buster) — cached per geo+date
        _gen_progress[style_key] = "Verifying facts with Firecrawl"
        verification = _get_verification_cached(news, style_key)

        _gen_progress[style_key] = "Writing the broadcast script"
        script = generate_script(news, style_key, verification=verification)

        # Save script for agent context
        _storage_put(f"audio/{date_str}/{style_key}_script.txt", script)

        _gen_progress[style_key] = "Generating audio with ElevenLabs"
        audio = generate_audio(script, style_key)

        _storage_put(audio_key, audio)
        print(f"[server] Saved {audio_key} ({len(audio):,} bytes)")

        # Update manifest (locked to prevent concurrent clobbering)
        with _manifest_lock:
            manifest = _load_manifest()

            # Ensure styles metadata is present
            if "styles" not in manifest:
                manifest["styles"] = {}
            manifest["styles"][style_key] = {
                "name": style["name"],
                "era": style.get("era", ""),
                "lang": style.get("lang", ""),
                "region": style.get("region", ""),
            }

            # Add to dates
            if "dates" not in manifest:
                manifest["dates"] = {}
            if date_str not in manifest["dates"]:
                manifest["dates"][date_str] = {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "styles": [],
                }
            if style_key not in manifest["dates"][date_str]["styles"]:
                manifest["dates"][date_str]["styles"].append(style_key)

            _save_manifest(manifest)
        _gen_progress.pop(style_key, None)

    except Exception as e:
        _gen_progress.pop(style_key, None)
        err_str = str(e).lower()
        if "quota" in err_str or "credit" in err_str or "402" in err_str or "insufficient" in err_str:
            _gen_errors[style_key] = "Audio quota exhausted — please top up ElevenLabs credits"
        else:
            _gen_errors[style_key] = "Generation failed"
        print(f"[server] ERROR generating {style_key}: {e}")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    return send_from_directory("web", "index.html")


@app.route("/audio/<path:filepath>")
def serve_audio(filepath):
    if filepath.endswith(".mp3"):
        mime = "audio/mpeg"
    elif filepath.endswith(".json"):
        mime = "application/json"
    else:
        return jsonify({"error": "Not found"}), 404

    data = _storage_get(f"audio/{filepath}")
    if data is None:
        return jsonify({"error": "Not found"}), 404

    from flask import Response
    return Response(data, mimetype=mime)


@app.route("/api/manifest")
def api_manifest():
    return jsonify(_load_manifest())


@app.route("/api/status/<date>/<style>")
def api_status(date, style):
    if not _valid_date(date):
        return jsonify({"error": "Invalid date format"}), 400
    if style not in STYLES:
        return jsonify({"error": "Unknown style"}), 404

    exists = _storage_exists(f"audio/{date}/{style}.mp3")
    step = _gen_progress.get(style, "")
    error = _gen_errors.get(style, "")
    return jsonify({"date": date, "style": style, "ready": exists, "step": step, "error": error})


@app.route("/api/generate/<date>/<style>", methods=["POST"])
def api_generate(date, style):
    if not _valid_date(date):
        return jsonify({"error": "Invalid date format"}), 400
    if date != _today_str():
        return jsonify({"error": "Generation is only available for today's date"}), 400
    if style not in STYLES:
        return jsonify({"error": "Unknown style"}), 404

    if _storage_exists(f"audio/{date}/{style}.mp3"):
        return jsonify({"status": "ready"})

    lock = _gen_locks.get(style)
    if lock and not lock.acquire(blocking=False):
        return jsonify({"status": "generating"})

    _gen_errors.pop(style, None)

    def run():
        try:
            _generate_style(date, style)
        finally:
            lock.release()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    return jsonify({"status": "generating"})


# ---------------------------------------------------------------------------
# Firecrawl Webhook Endpoints (called by ElevenLabs agent)
# ---------------------------------------------------------------------------

AGENT_WEBHOOK_SECRET = os.environ.get("AGENT_WEBHOOK_SECRET", "")


def _validate_webhook_secret():
    """Validate the X-Agent-Secret header on webhook requests."""
    if not AGENT_WEBHOOK_SECRET:
        return True  # No secret configured, allow all (development mode)
    header = request.headers.get("X-Agent-Secret", "")
    valid = hmac.compare_digest(header, AGENT_WEBHOOK_SECRET)
    if not valid:
        print(f"[webhook] REJECTED — invalid X-Agent-Secret header")
    return valid


@app.route("/api/agent/tools/search_news", methods=["POST"])
def tool_search_news():
    if not _validate_webhook_secret():
        return jsonify({"error": "Unauthorized"}), 401

    from firecrawl import FirecrawlApp
    from retrocast import _is_article_from_date

    data = request.get_json(silent=True) or {}
    query = data.get("query", "")
    region = data.get("region", "")
    print(f"[tool] search_news called — query={query!r} region={region!r}")
    if not query:
        return jsonify({"error": "query is required"}), 400

    full_query = f"{region} {query}".strip() if region else query
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        fc = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])
        print(f"[tool] search_news — calling Firecrawl: {full_query!r}")
        response = fc.search(full_query, limit=5, tbs="qdr:d", sources=["news"])
        results = []
        for item in (response.news or []):
            date = getattr(item, "date", "") or ""
            if not _is_article_from_date(date, today):
                continue
            results.append({
                "title": item.title or "",
                "url": item.url or "",
                "snippet": item.snippet or "",
                "date": date,
            })
        print(f"[tool] search_news — Firecrawl returned {len(results)} results")
        return jsonify({"results": results})
    except Exception as e:
        print(f"[tool] search_news — ERROR: {e}")
        return jsonify({"error": "News search failed"}), 500


@app.route("/api/agent/tools/fact_check", methods=["POST"])
def tool_fact_check():
    if not _validate_webhook_secret():
        return jsonify({"error": "Unauthorized"}), 401

    from firecrawl import FirecrawlApp

    data = request.get_json(silent=True) or {}
    claim = data.get("claim", "")
    print(f"[tool] fact_check called — claim={claim!r}")
    if not claim:
        return jsonify({"error": "claim is required"}), 400

    context = data.get("context", "")
    query = f'"{claim}" fact check verify'
    if context:
        query += f" {context}"

    try:
        fc = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])
        print(f"[tool] fact_check — calling Firecrawl: {query!r}")
        response = fc.search(query, limit=5, sources=["news"])
        results = []
        for item in (response.news or []):
            results.append({
                "title": item.title or "",
                "url": item.url or "",
                "snippet": item.snippet or "",
                "date": getattr(item, "date", "") or "",
            })
        print(f"[tool] fact_check — Firecrawl returned {len(results)} results")
        return jsonify({"results": results})
    except Exception as e:
        print(f"[tool] fact_check — ERROR: {e}")
        return jsonify({"error": "Fact check failed"}), 500


@app.route("/api/agent/tools/read_article", methods=["POST"])
def tool_read_article():
    if not _validate_webhook_secret():
        return jsonify({"error": "Unauthorized"}), 401

    from firecrawl import FirecrawlApp

    data = request.get_json(silent=True) or {}
    url = data.get("url", "")
    print(f"[tool] read_article called — url={url!r}")
    if not url:
        return jsonify({"error": "url is required"}), 400

    # SSRF guard: only allow public HTTPS URLs
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http"):
        return jsonify({"error": "Only HTTP(S) URLs are allowed"}), 400
    hostname = parsed.hostname or ""
    try:
        addr = ip_address(hostname)
        if addr.is_private or addr.is_loopback or addr.is_reserved:
            return jsonify({"error": "Internal URLs are not allowed"}), 400
    except ValueError:
        # Not a raw IP — check for localhost aliases
        if hostname in ("localhost", "metadata.google.internal"):
            return jsonify({"error": "Internal URLs are not allowed"}), 400

    try:
        fc = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])
        print(f"[tool] read_article — calling Firecrawl scrape: {url!r}")
        response = fc.scrape_url(url, formats=["markdown"])
        content = response.get("markdown", "") if isinstance(response, dict) else ""
        # Try attribute access if dict access fails
        if not content and hasattr(response, "markdown"):
            content = response.markdown or ""
        title = ""
        if isinstance(response, dict):
            title = response.get("metadata", {}).get("title", "")
        elif hasattr(response, "metadata") and response.metadata:
            title = getattr(response.metadata, "title", "") or ""
        # Truncate to ~3000 chars
        if len(content) > 3000:
            content = content[:3000] + "\n\n[Content truncated...]"
        print(f"[tool] read_article — got {len(content)} chars, title={title!r}")
        return jsonify({"title": title, "url": url, "content": content})
    except Exception as e:
        print(f"[tool] read_article — ERROR: {e}")
        return jsonify({"error": "Article fetch failed"}), 500


@app.route("/api/agent/tools/search_topic", methods=["POST"])
def tool_search_topic():
    if not _validate_webhook_secret():
        return jsonify({"error": "Unauthorized"}), 401

    from firecrawl import FirecrawlApp

    data = request.get_json(silent=True) or {}
    query = data.get("query", "")
    print(f"[tool] search_topic called — query={query!r}")
    if not query:
        return jsonify({"error": "query is required"}), 400

    try:
        fc = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])
        print(f"[tool] search_topic — calling Firecrawl: {query!r}")
        response = fc.search(query, limit=3)
        results = []
        # General web search returns results differently
        items = response.data if hasattr(response, "data") else []
        if not items and hasattr(response, "news"):
            items = response.news or []
        for item in items:
            results.append({
                "title": getattr(item, "title", "") or "",
                "url": getattr(item, "url", "") or "",
                "snippet": getattr(item, "snippet", getattr(item, "description", "")) or "",
            })
        print(f"[tool] search_topic — Firecrawl returned {len(results)} results")
        return jsonify({"results": results})
    except Exception as e:
        print(f"[tool] search_topic — ERROR: {e}")
        return jsonify({"error": "Topic search failed"}), 500


# ---------------------------------------------------------------------------
# Agent Provisioning Endpoint
# ---------------------------------------------------------------------------


@app.route("/api/agent/start", methods=["POST"])
def api_agent_start():
    if not _agent_rate_ok(request.remote_addr or "unknown"):
        return jsonify({"error": "Rate limit exceeded, try again later"}), 429

    from agent_config import get_agent_id, get_style_overrides, get_dynamic_variables
    from elevenlabs import ElevenLabs

    data = request.get_json(silent=True) or {}
    style_key = data.get("style", "")
    date_str = data.get("date", _today_str())

    if not _valid_date(date_str):
        return jsonify({"error": "Invalid date format"}), 400
    if style_key not in STYLES:
        return jsonify({"error": "Unknown style"}), 404

    try:
        print(f"[agent] Starting session for style={style_key!r} date={date_str!r}")

        # Pre-check ElevenLabs subscription quota
        client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
        try:
            sub = client.user.subscription.get()
            remaining = sub.character_limit - sub.character_count
            print(f"[agent] ElevenLabs quota: {sub.character_count}/{sub.character_limit} used ({remaining} remaining)")
            if remaining <= 0:
                print(f"[agent] BLOCKED — ElevenLabs character quota exhausted")
                return jsonify({"error": "Service temporarily unavailable — audio quota exhausted. Please try again later."}), 503
        except Exception as quota_err:
            print(f"[agent] WARNING: Could not check ElevenLabs quota: {quota_err}")
            # Continue anyway — the signed URL request will fail if truly exhausted

        agent_id = get_agent_id(style_key)
        if not agent_id:
            print(f"[agent] No agent_id found for style={style_key!r}")
            return jsonify({"error": "Agent not configured for this style"}), 404
        print(f"[agent] Using agent_id={agent_id}")

        # Load broadcast context if available
        broadcast_context = ""

        script_data = _storage_get(f"audio/{date_str}/{style_key}_script.txt")
        if script_data is not None:
            script_text = script_data.decode("utf-8")
            broadcast_context += f"\nToday's broadcast script:\n{script_text}\n"

        articles_data = _storage_get(f"audio/{date_str}/{style_key}_articles.json")
        if articles_data is not None:
            articles = json.loads(articles_data)
            parts = []
            for category, items in articles.items():
                for item in items:
                    parts.append(f"- {item.get('title', '')}: {item.get('snippet', '')[:100]}")
            if parts:
                broadcast_context += f"\nSource articles:\n" + "\n".join(parts[:15])

        # Get signed URL for the conversation
        signed_url_response = client.conversational_ai.conversations.get_signed_url(
            agent_id=agent_id
        )

        # Compute per-style overrides and dynamic variables
        overrides = get_style_overrides(style_key)
        dynamic_variables = get_dynamic_variables(style_key, broadcast_context)

        # Defensive: log the override payload size so we can spot regressions
        _override_size = len(json.dumps(overrides))
        print(f"[agent] Override payload size: {_override_size} chars, "
              f"dynamic_variables keys: {list(dynamic_variables.keys())}, "
              f"broadcast_context length: {len(broadcast_context)} chars")

        print(f"[agent] Session ready — signed URL obtained for {style_key}")
        return jsonify({
            "signed_url": signed_url_response.signed_url,
            "overrides": overrides,
            "dynamic_variables": dynamic_variables,
        })

    except Exception as e:
        err_str = str(e).lower()
        if "quota" in err_str or "credit" in err_str or "402" in err_str or "insufficient" in err_str:
            print(f"[server] ERROR starting agent (quota): {e}")
            return jsonify({"error": "Service temporarily unavailable — audio quota exhausted. Please try again later."}), 503
        print(f"[server] ERROR starting agent: {e}")
        return jsonify({"error": "Failed to start agent session"}), 500


# ---------------------------------------------------------------------------
# Catch-all: serve static files from web/ (globe.mp4, favicon, etc.)
# ---------------------------------------------------------------------------


@app.route("/<path:filepath>")
def serve_static(filepath):
    return send_from_directory("web", filepath)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Startup health check — warn about missing keys but still start
    _required = {
        "FIRECRAWL_API_KEY": "news fetching",
        "OPENAI_API_KEY": "script generation",
        "ELEVENLABS_API_KEY": "audio generation & agent",
    }
    _missing = [k for k in _required if not os.environ.get(k, "").strip()]
    if _missing:
        print("WARNING: Missing environment variables:")
        for k in _missing:
            print(f"  - {k}: {_required[k]}")
        print("Run 'python setup.py' for guided setup.\n")

    if _ON_REPLIT:
        print("Storage: Replit Object Storage")
    else:
        print(f"Storage: local filesystem ({_LOCAL_AUDIO_DIR})")

    port = int(os.environ.get("PORT", 5000))
    print(f"RetroCast server starting on http://localhost:{port}")
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=debug)
