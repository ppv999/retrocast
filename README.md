<div align="center">

# RetroCast

**Today's news. Yesterday's voice.**

Modern news is noise. RetroCast delivers today's headlines with the calm authority of vintage broadcast eras — AI-generated retro news bulletins across 4 countries and 8 styles, from 1960s Brazilian radio to 90s Indian television.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Built with Firecrawl](https://img.shields.io/badge/Built_with-Firecrawl-orange.svg)](https://firecrawl.dev)
[![Built with ElevenLabs](https://img.shields.io/badge/Built_with-ElevenLabs-black.svg)](https://elevenlabs.io)

</div>

<div align="center">

![RetroCast Demo](assets/demo.gif)

**[Watch the demo with sound →](https://youtu.be/tZRYseBIu_0)**

</div>

---

RetroCast fetches current news via [Firecrawl](https://firecrawl.dev), writes authentic broadcast scripts with [OpenAI GPT-4o](https://openai.com), and generates period-accurate audio with [ElevenLabs](https://elevenlabs.io) — complete with era-appropriate intro/outro music, multi-voice anchoring, and a live "Ask the Anchor" call-in feature where the anchor searches and fact-checks live using Firecrawl webhook tools.

## Features

- **8 broadcast styles** — 4 countries (India, UK, US, Brazil) × 2 formats (TV + Radio), each with era-authentic voice, scripting, and music
- **On-demand generation** — Click play, and today's news is fetched, scripted, and narrated in real time
- **Dual-anchor broadcasts** — TV formats use two AI anchors trading stories via ElevenLabs Text-to-Dialogue
- **Fact verification** — Firecrawl cross-checks headlines before they air, flagging disputed claims
- **"Ask the Anchor"** — Live voice conversations with the AI news anchor, who can search news and fact-check in real time using ElevenLabs Conversational AI + Firecrawl webhook tools
- **Multilingual** — Hindi, English, and Portuguese broadcasts with native-speaker voices
- **Date navigation** — Browse and replay past broadcasts

## How Firecrawl Powers RetroCast

Firecrawl is used at every stage — from content sourcing to live interaction.

### During Broadcast Generation

| Step | Firecrawl API | What it does |
|------|--------------|--------------|
| **News discovery** | `search` | Searches current news across 6 categories (politics, economy, science, sports, geopolitics, society), geo-filtered by country and region |
| **Fact verification** | `search` | Cross-checks the top stories against fact-checking sources; disputed claims are flagged so the anchor can address them on-air |

Every broadcast starts with **two Firecrawl calls** — one to find the news, one to verify it. This means Firecrawl shapes what the anchor says and how they say it (flagged claims get hedging language like "reports suggest" instead of stating them as fact).

### During Live "Ask the Anchor" Conversations

The ElevenAgents conversational AI agent is configured with **4 Firecrawl-powered webhook tools** that the anchor calls in real time during voice conversations:

| Webhook Tool | Firecrawl API | When the anchor calls it |
|-------------|--------------|------------------------|
| `search_news` | `search` (news sources) | User asks "What happened with…?" — anchor searches today's headlines by topic and region |
| `fact_check` | `search` (fact-check sources) | User asks "Is it true that…?" — anchor cross-checks the claim against fact-checking sources |
| `read_article` | `scrape_url` | User asks about a specific article — anchor scrapes and reads the full text to quote the original source |
| `search_topic` | `search` (general web) | User goes off-script — anchor runs a general web search on any topic |

These are server-side webhook endpoints (`/api/agent/tools`) that ElevenLabs calls during the conversation. The anchor decides which tool to use based on the user's question, calls the webhook, and weaves the Firecrawl results into its spoken response — all in real time.

## How ElevenLabs Powers RetroCast

ElevenLabs is used for all audio generation and the live voice agent.

### Voice Generation

| Feature | ElevenLabs API | How it's used |
|---------|---------------|---------------|
| **Dual-anchor TV broadcasts** | Text-to-Dialogue | TV formats (Doordarshan, BBC, CBS/NBC, Jornal Nacional) use two distinct AI voices trading stories back and forth — a single script is split into a natural dialogue |
| **Solo radio broadcasts** | Text-to-Speech | Radio formats (Akashvani, BBC World Service, NPR, Repórter Esso) use a single narrator voice with era-appropriate pacing |
| **16 unique voices** | Voice Library | Each of the 8 styles has its own voice (or voice pair), matched to geographic origin and era — a 1970s American anchor sounds nothing like a 1980s Hindi newsreader |
| **Multilingual output** | Multilingual TTS | Hindi, English, and Portuguese broadcasts use native-speaker voices, not translated English |

### Live Conversational AI ("Ask the Anchor")

| Feature | ElevenLabs API | How it's used |
|---------|---------------|---------------|
| **Voice agent** | Conversational AI | Each broadcast style has a unique agent persona — the anchor stays in character during the entire conversation |
| **Signed URLs** | Conversation Sessions | Server provisions short-lived signed URLs so the browser connects directly to ElevenLabs without exposing API keys |
| **Webhook tools** | Tool Use | 4 Firecrawl-powered tools are registered as webhooks — ElevenLabs calls them server-side when the anchor needs to search or fact-check |
| **Dynamic overrides** | Agent Overrides | The agent's persona, language, and first message are overridden per-style at session start — one agent definition serves all 8 styles |

## Broadcast Styles

| Style | Country | Format | Era | Language |
|-------|---------|--------|-----|----------|
| Doordarshan News | India | TV | 1990s | Hindi |
| All India Radio (Akashvani) | India | Radio | 1980s | Hindi |
| BBC Television News | UK | TV | 1980s | English |
| BBC World Service | UK | Radio | 1980s | English |
| Network News (CBS/NBC) | US | TV | 1970s | English |
| NPR Morning Edition | US | Radio | 1990s | English |
| Jornal Nacional | Brazil | TV | 1980s | Portuguese |
| Repórter Esso | Brazil | Radio | 1960s | Portuguese |

Each style has its own ElevenLabs voice (or voice pair for dual-anchor formats), scripting conventions faithful to the era, and period-appropriate intro/outro music.

## Pipeline

```
  Firecrawl             Firecrawl             OpenAI              ElevenLabs
┌──────────┐         ┌──────────┐         ┌──────────┐         ┌──────────┐
│  Fetch   │────────▶│  Verify  │────────▶│  Script  │────────▶│  Audio   │
│  News    │         │  Facts   │         │  Write   │         │  Generate│
└──────────┘         └──────────┘         └──────────┘         └──────────┘
 Search 6 categories   Cross-check top      GPT-4o writes an     Text-to-Dialogue
 by country/region     stories against      era-authentic         for dual-anchor,
 via Firecrawl news    fact-check sources    broadcast script      TTS for solo, then
 search API            and flag disputes     in the target lang    merge with intro/
                                                                   outro music
```

1. **Fetch** — Firecrawl searches current news across 6 categories (politics, economy, science, sports, geopolitics, society), geo-filtered by country
2. **Verify** — Top articles are cross-checked against fact-check sources via Firecrawl; disputed claims are flagged for the anchor to address
3. **Script** — OpenAI GPT-4o writes a ~3-minute broadcast script following the style's era conventions, language, and editorial voice
4. **Generate** — ElevenLabs converts the script to speech (Text-to-Dialogue for dual-anchor TV formats, standard TTS for radio), then pydub assembles the final MP3 with intro/outro music

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  index.html — Single-page app                        │    │
│  │  • Audio player with date navigation                 │    │
│  │  • On-demand generation (poll for progress)          │    │
│  │  • "Ask the Anchor" via ElevenLabs Conversation SDK  │    │
│  └───────────────────────┬─────────────────────────────┘    │
└──────────────────────────┼──────────────────────────────────┘
                           │ HTTP
┌──────────────────────────┼──────────────────────────────────┐
│  server.py — Flask       │                                   │
│  ├─ GET  /api/manifest   │  List available broadcasts        │
│  ├─ GET  /api/status     │  Generation progress              │
│  ├─ POST /api/generate   │  Trigger background generation    │
│  ├─ POST /api/agent/start│  Provision live call-in session   │
│  └─ POST /api/agent/tools│  Webhook tools for live agent     │
└──────────────────────────┼──────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────┐
│  retrocast.py — Core pipeline                                │
│  ├─ fetch_news()         │  Firecrawl news search API        │
│  ├─ verify_news()        │  Firecrawl fact-checking           │
│  ├─ generate_script()    │  OpenAI GPT-4o                     │
│  └─ generate_audio()     │  ElevenLabs TTS / Text-to-Dialogue │
└──────────────────────────┴──────────────────────────────────┘
```

Concurrency is handled with per-style generation locks (only one generation per style at a time) and a thread-safe manifest for tracking completed broadcasts.

## Quick Start

```bash
git clone https://github.com/ppv999/retrocast.git
cd retrocast
pip install -r requirements.txt
cp .env.example .env         # Add your API keys
python setup.py              # Validates keys, creates ElevenLabs agent
python server.py             # http://localhost:5000
```

> **Requires [ffmpeg](https://ffmpeg.org/)** for audio assembly — `brew install ffmpeg` on macOS, `apt install ffmpeg` on Linux.

You'll need API keys from three services (all have free tiers):

| Service | What it does | Get a key |
|---------|-------------|-----------|
| [Firecrawl](https://firecrawl.dev) | Searches and extracts news articles | [firecrawl.dev](https://firecrawl.dev) |
| [OpenAI](https://openai.com) | Writes broadcast scripts (GPT-4o) | [platform.openai.com](https://platform.openai.com/api-keys) |
| [ElevenLabs](https://elevenlabs.io) | Text-to-speech and live voice agent | [elevenlabs.io](https://elevenlabs.io/app/settings/api-keys) |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `FIRECRAWL_API_KEY` | Yes | Firecrawl API key |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `ELEVENLABS_API_KEY` | Yes | ElevenLabs API key |
| `AGENT_BASE_URL` | No | Public URL for webhook tools |
| `PORT` | No | Server port (default: `5000`) |

## Deploy on Replit

1. Import this repo from GitHub
2. Add your API keys as **Secrets** (`FIRECRAWL_API_KEY`, `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`)
3. Open the **Shell** tab and run `python setup.py`
4. Set `AGENT_BASE_URL` to your Replit URL (e.g., `https://retrocast.yourusername.replit.app`)
5. Click **Run**

The included `replit.nix` ensures ffmpeg is available.

## Project Structure

```
retrocast/
├── server.py            # Flask server — API endpoints, static serving, rate limiting
├── retrocast.py         # Core pipeline — news fetching, verification, script & audio generation
├── agent_config.py      # ElevenLabs Conversational AI agent setup and webhook tools
├── setup.py             # Interactive setup wizard — API key validation, agent creation
├── generate_all.py      # Batch generation script (all 8 styles at once)
├── requirements.txt     # Python dependencies
├── assets/              # Intro/outro music files for each broadcast style
├── web/
│   ├── index.html       # Single-page frontend (player, globe, conversation UI)
│   ├── favicon.svg      # Wireframe globe icon
│   └── audio/           # Generated broadcasts by date (gitignored)
├── .env.example         # Environment variable template
├── .replit              # Replit run configuration
└── replit.nix           # Replit system dependencies (Python 3.11, ffmpeg)
```

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

The most impactful contributions:
- **New countries/styles** — Add a new broadcast era (see the style guide in `.claude/commands/add-country.md`)
- **Voice improvements** — Better voice matching, pronunciation tuning
- **Frontend polish** — Animations, mobile experience, accessibility

## Security

If you discover a security vulnerability, please report it responsibly. See [SECURITY.md](SECURITY.md) for details.

## License

[MIT](LICENSE) — use it, fork it, broadcast it.
