# RetroCast

A Flask web application that delivers "Today's news with Yesterday's voice." It fetches current news, generates authentic broadcast scripts in various vintage styles, and produces period-accurate audio bulletins using AI.

## Architecture

- **Backend:** Python / Flask (`server.py`)
- **Frontend:** Single-page HTML/JS app in `web/`
- **Core pipeline:** `retrocast.py` — news fetching, script generation, audio production
- **Agent config:** `agent_config.py` — ElevenLabs Conversational AI setup
- **Setup wizard:** `setup.py` — validates API keys and provisions the ElevenLabs agent

## File Storage

All generated files (audio MP3s, scripts, articles JSON, manifest) are stored in **Replit Object Storage** — not the local filesystem. This makes the app compatible with Autoscale deployments where the filesystem is ephemeral.

Storage helpers in `server.py`:
- `_storage_put(key, data)` — upload bytes or string
- `_storage_get(key)` — download as bytes (returns `None` if not found)
- `_storage_exists(key)` — check existence

Key prefix structure: `audio/<date>/<style_key>.mp3`, `audio/<date>/<style_key>_script.txt`, `audio/<date>/<style_key>_articles.json`, `audio/manifest.json`

The `Client` is instantiated with `bucket_id=os.environ.get("DEFAULT_OBJECT_STORAGE_BUCKET_ID")` to bypass the sidecar lookup (which requires `.replit` configuration that can't be edited by the agent).

## Dependencies

Python: flask, python-dotenv, openai, elevenlabs, firecrawl-py, pydub, replit-object-storage
System: ffmpeg (for audio processing via pydub)

## API Keys Required

- `FIRECRAWL_API_KEY` — news fetching
- `OPENAI_API_KEY` — script generation
- `ELEVENLABS_API_KEY` — audio generation & conversational agent
- `ELEVENLABS_AGENT_ID` — Ask the Anchor feature (created via `python setup.py`)

## Broadcast Styles

8 styles across 4 countries:
- **India:** Doordarshan (90s TV), All India Radio (80s Radio)
- **UK:** BBC Television News (80s TV), BBC World Service (80s Radio)
- **US:** Network News (70s TV), NPR Morning Edition (90s Radio)
- **Brazil:** Jornal Nacional (80s TV), Repórter Esso (60s Radio)

## Running

The app runs on port 5000. Workflow: `python server.py`
