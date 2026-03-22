#!/usr/bin/env python3
"""RetroCast Setup Wizard — validates API keys and creates the ElevenLabs agent.

Usage:
    python setup.py          # Guided interactive setup
    python setup.py --check  # Validate only (exit 0 if all OK, 1 otherwise)
"""

import os
import secrets
import shutil
import sys

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
ENV_EXAMPLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.example")

AGENT_NAME = "RetroCast Anchor"

REQUIRED_KEYS = ["FIRECRAWL_API_KEY", "OPENAI_API_KEY", "ELEVENLABS_API_KEY"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _print_header(title: str):
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print(f"{'=' * 50}\n")


def _print_check(ok: bool, label: str, detail: str = ""):
    icon = "[OK]" if ok else "[FAIL]"
    msg = f"  {icon} {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)


def _read_env_file() -> dict:
    """Parse .env file into a dict (simple key=value, ignoring comments)."""
    env = {}
    if not os.path.exists(ENV_PATH):
        return env
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Remove surrounding quotes
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                env[key] = value
    return env


def _write_env_var(key: str, value: str):
    """Set a key in the .env file (update if exists, append if not)."""
    lines = []
    found = False
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            lines = f.readlines()

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, _, _ = stripped.partition("=")
            if k.strip() == key:
                new_lines.append(f"{key}={value}\n")
                found = True
                continue
        # Also uncomment lines like "# KEY=" if they match
        if stripped.startswith("#") and key in stripped:
            k_part = stripped.lstrip("# ").partition("=")[0].strip()
            if k_part == key:
                new_lines.append(f"{key}={value}\n")
                found = True
                continue
        new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}\n")

    with open(ENV_PATH, "w") as f:
        f.writelines(new_lines)


def _get_env(key: str) -> str:
    """Get env var from os.environ (includes .env via dotenv)."""
    return os.environ.get(key, "").strip()


def _prompt_key(key: str, description: str, url: str) -> str:
    """Prompt user to paste an API key."""
    print(f"\n  {key} is not set.")
    print(f"  Get one at: {url}")
    value = input(f"  Paste your {description}: ").strip()
    if value:
        _write_env_var(key, value)
        os.environ[key] = value
    return value


# ---------------------------------------------------------------------------
# Step 1: Ensure .env exists
# ---------------------------------------------------------------------------


def ensure_env_file():
    """Create .env from .env.example if it doesn't exist."""
    if os.path.exists(ENV_PATH):
        print(f"  Found .env")
        return

    if os.path.exists(ENV_EXAMPLE_PATH):
        shutil.copy2(ENV_EXAMPLE_PATH, ENV_PATH)
        print(f"  Created .env from .env.example")
    else:
        with open(ENV_PATH, "w") as f:
            f.write("# RetroCast environment variables\n")
        print(f"  Created empty .env")


# ---------------------------------------------------------------------------
# Step 2: Validate API keys
# ---------------------------------------------------------------------------


def validate_firecrawl(interactive: bool) -> bool:
    key = _get_env("FIRECRAWL_API_KEY")
    if not key:
        if interactive:
            key = _prompt_key("FIRECRAWL_API_KEY", "Firecrawl API key", "https://firecrawl.dev")
        if not key:
            _print_check(False, "Firecrawl", "FIRECRAWL_API_KEY not set")
            return False

    try:
        from firecrawl import FirecrawlApp
        fc = FirecrawlApp(api_key=key)
        fc.search("test", limit=1)
        _print_check(True, "Firecrawl")
        return True
    except Exception as e:
        _print_check(False, "Firecrawl", str(e)[:80])
        return False


def validate_openai(interactive: bool) -> bool:
    key = _get_env("OPENAI_API_KEY")
    if not key:
        if interactive:
            key = _prompt_key("OPENAI_API_KEY", "OpenAI API key", "https://platform.openai.com/api-keys")
        if not key:
            _print_check(False, "OpenAI", "OPENAI_API_KEY not set")
            return False

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        client.models.list()
        _print_check(True, "OpenAI")
        return True
    except Exception as e:
        _print_check(False, "OpenAI", str(e)[:80])
        return False


def validate_elevenlabs(interactive: bool) -> bool:
    key = _get_env("ELEVENLABS_API_KEY")
    if not key:
        if interactive:
            key = _prompt_key("ELEVENLABS_API_KEY", "ElevenLabs API key", "https://elevenlabs.io/app/settings/api-keys")
        if not key:
            _print_check(False, "ElevenLabs", "ELEVENLABS_API_KEY not set")
            return False

    try:
        from elevenlabs import ElevenLabs
        client = ElevenLabs(api_key=key)
        client.voices.get_all()
        _print_check(True, "ElevenLabs")
        return True
    except Exception as e:
        _print_check(False, "ElevenLabs", str(e)[:80])
        return False


# ---------------------------------------------------------------------------
# Step 3: ElevenLabs Agent Setup
# ---------------------------------------------------------------------------


def setup_agent(interactive: bool) -> bool:
    """Ensure an ElevenLabs Conversational AI agent exists."""
    key = _get_env("ELEVENLABS_API_KEY")
    if not key:
        _print_check(False, "ElevenLabs Agent", "ELEVENLABS_API_KEY required first")
        return False

    from elevenlabs import ElevenLabs

    client = ElevenLabs(api_key=key)
    agent_id = _get_env("ELEVENLABS_AGENT_ID")

    # If agent ID is set, validate it
    if agent_id:
        try:
            agent = client.conversational_ai.agents.get(agent_id=agent_id)
            _print_check(True, "ElevenLabs Agent", f"'{agent.name}' ({agent_id})")
            return True
        except Exception:
            print(f"  WARNING: ELEVENLABS_AGENT_ID={agent_id} is invalid, searching for agent...")
            agent_id = ""

    # Search for existing agent by name
    try:
        agents_response = client.conversational_ai.agents.list()
        agents = agents_response.agents if hasattr(agents_response, "agents") else []
        existing = None
        for a in agents:
            if a.name == AGENT_NAME:
                existing = a
                break

        if existing:
            agent_id = existing.agent_id
            if interactive:
                answer = input(f"  Found agent '{AGENT_NAME}' ({agent_id}). Use this? [Y/n] ").strip()
                if answer.lower() == "n":
                    existing = None
                    agent_id = ""

            if agent_id:
                _write_env_var("ELEVENLABS_AGENT_ID", agent_id)
                os.environ["ELEVENLABS_AGENT_ID"] = agent_id
                _print_check(True, "ElevenLabs Agent", f"'{AGENT_NAME}' ({agent_id})")
                return True
    except Exception as e:
        print(f"  WARNING: Could not list agents: {e}")

    # Create new agent
    if not interactive:
        _print_check(False, "ElevenLabs Agent", "ELEVENLABS_AGENT_ID not set — run `python setup.py` (without --check)")
        return False

    answer = input(f"  No agent found. Create '{AGENT_NAME}'? [Y/n] ").strip()
    if answer.lower() == "n":
        _print_check(False, "ElevenLabs Agent", "Skipped by user")
        return False

    try:
        from agent_config import BASE_AGENT_PROMPT
        from elevenlabs.types import (
            AgentConfig,
            ConversationalConfig,
            PromptAgentApiModelInput,
            TtsConversationalConfigInput,
        )
        from retrocast import STYLES

        default_voice = STYLES["bbc"]["default_voice"]

        agent = client.conversational_ai.agents.create(
            name=AGENT_NAME,
            conversation_config=ConversationalConfig(
                agent=AgentConfig(
                    prompt=PromptAgentApiModelInput(
                        prompt=BASE_AGENT_PROMPT,
                        llm="gpt-4o",
                    ),
                    first_message=(
                        "Good evening. The broadcast is concluded. "
                        "You're welcome to ask about any of today's stories. "
                        "May I know your name?"
                    ),
                    language="en",
                ),
                tts=TtsConversationalConfigInput(
                    voice_id=default_voice,
                ),
            ),
        )

        agent_id = agent.agent_id
        _write_env_var("ELEVENLABS_AGENT_ID", agent_id)
        os.environ["ELEVENLABS_AGENT_ID"] = agent_id
        _print_check(True, "ElevenLabs Agent", f"Created '{AGENT_NAME}' ({agent_id})")
        return True

    except Exception as e:
        _print_check(False, "ElevenLabs Agent", f"Creation failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Step 4: Configure webhook tools
# ---------------------------------------------------------------------------


def setup_webhooks(interactive: bool) -> bool:
    """Configure webhook tools on the agent if AGENT_BASE_URL is set."""
    base_url = _get_env("AGENT_BASE_URL")
    agent_id = _get_env("ELEVENLABS_AGENT_ID")

    if not base_url:
        print("  [SKIP] Webhook tools — AGENT_BASE_URL not set")
        print("         'Ask the Anchor' needs a public URL to receive webhook calls.")
        print("         Set AGENT_BASE_URL in .env and re-run setup.")
        return True  # Not a failure, just skipped

    if not agent_id:
        print("  [SKIP] Webhook tools — no agent configured")
        return False

    try:
        from agent_config import configure_default_agent
        configure_default_agent(base_url, agent_id=agent_id)
        _print_check(True, "Webhook tools", f"configured for {base_url}")
        return True
    except Exception as e:
        _print_check(False, "Webhook tools", str(e)[:80])
        return False


# ---------------------------------------------------------------------------
# Step 5: Generate webhook secret
# ---------------------------------------------------------------------------


def ensure_webhook_secret():
    """Generate AGENT_WEBHOOK_SECRET if not set."""
    if _get_env("AGENT_WEBHOOK_SECRET"):
        return
    secret = secrets.token_urlsafe(32)
    _write_env_var("AGENT_WEBHOOK_SECRET", secret)
    os.environ["AGENT_WEBHOOK_SECRET"] = secret
    print("  Generated AGENT_WEBHOOK_SECRET")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    check_only = "--check" in sys.argv
    interactive = not check_only and sys.stdin.isatty()

    _print_header("RetroCast Setup")

    # Load existing .env
    if not check_only:
        ensure_env_file()

    # Load .env into os.environ
    from dotenv import load_dotenv
    load_dotenv(ENV_PATH, override=True)

    # Validate API keys
    print("\nAPI Keys:")
    results = {}
    results["firecrawl"] = validate_firecrawl(interactive)
    results["openai"] = validate_openai(interactive)
    results["elevenlabs"] = validate_elevenlabs(interactive)

    # Agent setup (requires ElevenLabs key)
    print("\nElevenLabs Agent:")
    if results["elevenlabs"]:
        results["agent"] = setup_agent(interactive)
    else:
        _print_check(False, "ElevenLabs Agent", "fix ElevenLabs API key first")
        results["agent"] = False

    # Webhook secret
    if not check_only:
        ensure_webhook_secret()

    # Webhook tools
    print("\nWebhook Tools:")
    if results["agent"]:
        results["webhooks"] = setup_webhooks(interactive)
    else:
        print("  [SKIP] Webhook tools — no agent configured")
        results["webhooks"] = False

    # Summary
    _print_header("Summary")
    all_required = all(results.get(k, False) for k in ["firecrawl", "openai", "elevenlabs", "agent"])
    for key, ok in results.items():
        label = {
            "firecrawl": "Firecrawl API",
            "openai": "OpenAI API",
            "elevenlabs": "ElevenLabs API",
            "agent": "ElevenLabs Agent",
            "webhooks": "Webhook Tools",
        }.get(key, key)
        _print_check(ok, label)

    if all_required:
        print("\n  Ready! Start the server with:")
        print("    python server.py\n")
    else:
        print("\n  Some checks failed. Fix the issues above and re-run:")
        print("    python setup.py\n")

    sys.exit(0 if all_required else 1)


if __name__ == "__main__":
    main()
