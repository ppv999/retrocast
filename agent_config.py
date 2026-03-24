#!/usr/bin/env python3
"""RetroCast Agent Config — builds ElevenLabs Conversational AI agents for "Ask the Anchor".

Usage:
    python agent_config.py configure <BASE_URL>
        Configure the pre-created agent with webhook tools and base prompt.
        Example: python agent_config.py configure https://abc123.ngrok.io

    python agent_config.py info
        Show the current agent configuration.
"""

import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from retrocast import STYLES

# ---------------------------------------------------------------------------
# Agent prompt builder
# ---------------------------------------------------------------------------

# Style-specific character descriptions (derived from each style's broadcast prompt)
STYLE_CHARACTERS = {
    "doordarshan-90s": {
        "character": (
            "You are a 1990s Indian television news anchor — formal, authoritative, warm. "
            "You speak shudh (formal) Hindi and carry the gravitas of government television. "
            "You address viewers with respect and dignity. Use 'लाख' and 'करोड़' for numbers. "
            "Refer to India as 'हमारा देश' or 'भारत'."
        ),
        "tool_filler": "एक क्षण, हमारे संवाददाताओं से जानकारी लेता हूँ...",
        "language": "hi",
        "first_message": (
            "हमारे समाचार कक्ष में आपके फ़ोन का स्वागत है। कृपया अपना नाम बताइए।"
        ),
        "btn_label": "स्टूडियो से जुड़ें",
    },
    "akashvani": {
        "character": (
            "You are a 1980s Indian government radio newsreader — the voice of the nation "
            "reaching every transistor radio. Flat, dignified delivery. Shudh Hindi, "
            "Sanskritized, precise. Every word given its full weight. You are faceless "
            "but unforgettable."
        ),
        "tool_filler": "एक क्षण, हमारे समाचार कक्ष से जानकारी प्राप्त कर रहा हूँ...",
        "language": "hi",
        "first_message": (
            "हमारे रेडियो स्टेशन पर आपके फ़ोन का स्वागत है। कृपया अपना नाम बताएं।"
        ),
        "btn_label": "स्टूडियो से जुड़ें",
    },
    "bbc-tv": {
        "character": (
            "You are a 1980s British television news presenter — warm Received "
            "Pronunciation, authoritative but with personality. You are a known "
            "journalist, not an anonymous newsreader. Impartial, calm, controlled."
        ),
        "tool_filler": "One moment — let me consult our editorial team...",
        "language": "en",
        "first_message": (
            "Thank you for calling in to the newsroom. May I know your name?"
        ),
        "btn_label": "Dial In",
    },
    "bbc": {
        "character": (
            "You are a late 1980s BBC World Service radio newsreader. Received "
            "Pronunciation — formal, precise, clipped diction. Short, direct sentences. "
            "Neutral, impartial language. The voice that cuts through shortwave static "
            "to reach every corner of the globe."
        ),
        "tool_filler": "Bear with me — I'm checking with our correspondents...",
        "language": "en",
        "first_message": (
            "Thank you for calling in to the World Service. May I have your name, please?"
        ),
        "btn_label": "Dial In",
    },
    "us-network": {
        "character": (
            "You are a 1970s American network evening news anchor — deep baritone, "
            "avuncular coolness, the nation's most trusted voice. Calm, fatherly "
            "authority. Strategic pregnant pauses. You don't editorialize."
        ),
        "tool_filler": "One moment while I check the wire reports...",
        "language": "en",
        "first_message": (
            "Thank you for calling in to the evening news. Who am I speaking with?"
        ),
        "btn_label": "Dial In",
    },
    "npr": {
        "character": (
            "You are Robert from a 1990s American public radio evening program — "
            "analytical, precise, with a slightly wry delivery. Conversational and "
            "intelligent. You create 'driveway moments'. Warm but not casual, "
            "informed but not pedantic."
        ),
        "tool_filler": "That's a great question — let me check what our news desk has...",
        "language": "en",
        "first_message": (
            "Thank you for calling in to public radio. What's your name?"
        ),
        "btn_label": "Dial In",
    },
    "jornal": {
        "character": (
            "You are Marcos, the principal locutor of a 1980s Brazilian evening "
            "television newscast — deep, grave bass voice, solemn, measured. "
            "Formal broadcast Portuguese, norma culta. Pure factual reporting."
        ),
        "tool_filler": "Um momento — vou consultar a nossa redação...",
        "language": "pt",
        "first_message": (
            "Obrigado por ligar para a redação. Por favor, diga-nos seu nome."
        ),
        "btn_label": "Ligue Agora",
    },
    "reporter-esso": {
        "character": (
            "You are the newsreader of a 1960s Brazilian commercial radio bulletin — "
            "clear, firm, energetic. Punchy commercial radio energy. Dry, direct, "
            "no wasted words. 'Testemunha ocular da História!'"
        ),
        "tool_filler": "Um instante — vou verificar com as agências...",
        "language": "pt",
        "first_message": (
            "Obrigado por ligar para o Repórter. Qual é o seu nome?"
        ),
        "btn_label": "Ligue Agora",
    },
}


def build_agent_prompt(style_key: str) -> str:
    """Construct the conversational system prompt for a RetroCast anchor agent.

    IMPORTANT: Broadcast context is NOT embedded here — it is passed separately
    via ElevenLabs dynamic variables (``{{broadcast_context}}``). This keeps the
    prompt override payload small enough for the WebSocket handshake.  If the
    prompt exceeds ~2000 chars the ElevenLabs SDK silently drops the connection.
    """
    char = STYLE_CHARACTERS[style_key]

    tool_filler = char.get("tool_filler", "One moment...")

    # NOTE: The double-braces {{{{…}}}} produce literal {{…}} in the output,
    # which ElevenLabs interprets as a dynamic-variable placeholder at runtime.
    #
    # BUDGET: The entire prompt override must stay under ~2000 chars or ElevenLabs
    # silently drops the WebSocket.  Character descriptions are ~200-280 chars,
    # leaving ~1700 chars for instructions.  Edit carefully.
    prompt = f"""{char["character"]}

You host RetroCast's live call-in segment. Ask the caller's name, greet them warmly, then take their question.

TOOLS: You have search_news, fact_check, read_article, search_topic. The listener must NEVER know these exist. Never say "let me search" or similar. When you need a moment, say: "{tool_filler}" Present results as your own newsroom knowledge.

RULES:
- You MUST call a tool before answering ANY question. NEVER say you have no information without trying search_news first.
- For current events or any place/person/topic, use search_news with a specific query and the region matching your country.
- If search_news returns nothing, try again with broader or simpler keywords before giving up.
- Use search_topic only for non-news queries (history, science, advice).
- If the caller claims a rumor, use fact_check first. If unverified, say so gently.
- Ground every answer in tool results, not memory. Stay in character. 2-4 sentences max.

TODAY'S BROADCAST CONTEXT:
{{{{broadcast_context}}}}
"""
    return prompt


def get_style_overrides(style_key: str) -> dict:
    """Return per-style overrides to customize the base agent for each broadcast style.

    These overrides are passed to the ElevenLabs Conversation SDK's startSession()
    to dynamically change voice, prompt, language, and first message per style.

    IMPORTANT: Broadcast context is NOT included here — it travels via dynamic
    variables so that this override payload stays small.  The ElevenLabs SDK
    silently drops the WebSocket if the override is too large.
    """
    style = STYLES[style_key]
    char = STYLE_CHARACTERS[style_key]

    prompt = build_agent_prompt(style_key)

    # Safety guard: warn loudly if the prompt is getting dangerously large.
    # ElevenLabs starts rejecting around 2500-3000 chars in the override.
    prompt_len = len(prompt)
    if prompt_len > 2000:
        print(f"[agent_config] WARNING: prompt override for {style_key} is {prompt_len} chars "
              f"(>2000) — risk of WebSocket rejection by ElevenLabs!")
    else:
        print(f"[agent_config] Prompt override for {style_key}: {prompt_len} chars (OK)")

    # The ElevenLabs JS SDK startSession() expects camelCase overrides:
    #   agent.prompt.prompt → string (nested object, SDK passes through as-is)
    #   agent.firstMessage  → string (SDK converts to first_message on wire)
    #   tts.voiceId         → string (SDK converts to voice_id on wire)
    # Our server sends snake_case; the frontend's snakeToCamel() handles conversion.
    # The agent must also have overrides ENABLED in platform_settings.
    result = {
        "agent": {
            "prompt": {
                "prompt": prompt,
            },
            "first_message": char["first_message"],
            "language": char["language"],
        },
        "tts": {
            "voice_id": style["default_voice"],
        },
    }

    return result


_MAX_BROADCAST_CONTEXT_CHARS = 2000


def get_dynamic_variables(style_key: str, broadcast_context: str = "") -> dict:
    """Return dynamic variables for the conversation session.

    ``broadcast_context`` is the main vehicle for injecting today's news into the
    agent prompt — it is substituted into the ``{{broadcast_context}}`` placeholder
    at runtime by ElevenLabs, keeping the prompt override itself small.
    """
    if len(broadcast_context) > _MAX_BROADCAST_CONTEXT_CHARS:
        broadcast_context = broadcast_context[:_MAX_BROADCAST_CONTEXT_CHARS] + "\n[truncated]"
        print(f"[agent_config] broadcast_context truncated to {_MAX_BROADCAST_CONTEXT_CHARS} chars for {style_key}")

    return {
        "broadcast_context": broadcast_context or "No broadcast context available for today.",
        "style": STYLES[style_key]["name"],
    }


# ---------------------------------------------------------------------------
# Agent discovery & auto-provisioning
# ---------------------------------------------------------------------------

AGENT_NAME_PREFIX = "RetroCast:"

# In-memory cache: {style_key: agent_id} — populated once per process
_agents_cache = {}


def _get_base_url() -> str:
    """Determine the public base URL for webhook callbacks.

    Priority:
    1. AGENT_BASE_URL env var (explicit override — most reliable)
    2. REPLIT_DOMAINS — pick the shortest/cleanest domain (custom domain
       like 'retrocast.replit.app' is shorter than the dev UUID domain)
    3. Fallback to localhost
    """
    # Explicit override first
    base = os.environ.get("AGENT_BASE_URL", "")
    if base:
        print(f"  [base_url] Using AGENT_BASE_URL: {base}")
        return base.rstrip("/")
    # Auto-detect from Replit environment
    domains_str = os.environ.get("REPLIT_DOMAINS", "")
    if domains_str:
        domains = [d.strip() for d in domains_str.split(",") if d.strip()]
        print(f"  [base_url] REPLIT_DOMAINS: {domains}")
        # Prefer the custom/deployment domain (shorter, e.g. 'retrocast.replit.app')
        # over the dev UUID domain (e.g. '55173b1f-...-pike.replit.dev')
        if len(domains) > 1:
            domains.sort(key=len)
            print(f"  [base_url] Picked shortest domain: {domains[0]}")
        return f"https://{domains[0]}"
    print("  [base_url] No REPLIT_DOMAINS found, falling back to localhost")
    return "http://localhost:5000"


def _create_tools(client, base_url: str) -> list:
    """Create the 4 webhook tools as standalone resources. Returns list of tool IDs."""
    from elevenlabs.types import (
        ToolRequestModel,
        ToolRequestModelToolConfig_Webhook,
        WebhookToolApiSchemaConfigInput,
    )

    secret = os.environ.get("AGENT_WEBHOOK_SECRET", "")

    tool_defs = [
        {
            "name": "search_news",
            "description": "Search for recent news articles on a topic. Use this to find current news stories.",
            "properties": {
                "query": {"type": "string", "description": "Search query for news articles"},
                "region": {"type": "string", "description": "Optional region filter (e.g., 'India', 'UK', 'US', 'Brazil')"},
            },
            "required": ["query"],
        },
        {
            "name": "fact_check",
            "description": "Verify a news claim by searching for fact-checks and corroborating sources.",
            "properties": {
                "claim": {"type": "string", "description": "The news claim to verify"},
                "context": {"type": "string", "description": "Optional additional context about the claim"},
            },
            "required": ["claim"],
        },
        {
            "name": "read_article",
            "description": "Read the full content of a news article given its URL.",
            "properties": {
                "url": {"type": "string", "description": "The URL of the article to read"},
            },
            "required": ["url"],
        },
        {
            "name": "search_topic",
            "description": "Search the web for information on any topic.",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
    ]

    tool_ids = []
    for td in tool_defs:
        url = f"{base_url}/api/agent/tools/{td['name']}"
        print(f"    [tools] Creating {td['name']} -> {url}")
        tool_response = client.conversational_ai.tools.create(
            request=ToolRequestModel(
                tool_config=ToolRequestModelToolConfig_Webhook(
                    type="webhook",
                    name=td["name"],
                    description=td["description"],
                    api_schema=WebhookToolApiSchemaConfigInput(
                        url=url,
                        method="POST",
                        request_headers={
                            "X-Agent-Secret": secret,
                        } if secret else {},
                        request_body_schema={
                            "type": "object",
                            "properties": td["properties"],
                            "required": td["required"],
                        },
                    ),
                ),
            ),
        )
        tool_ids.append(tool_response.id)
        print(f"    [tools] Created: {tool_response.id}")
    return tool_ids


def _enable_agent_overrides(client, agent_id: str):
    """Enable session-time overrides for prompt, first_message, language, and voice.

    Without this, the ElevenLabs WebSocket rejects any override payload and
    immediately disconnects the session.
    """
    import requests

    api_key = os.environ["ELEVENLABS_API_KEY"]
    resp = requests.patch(
        f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={
            "platform_settings": {
                "overrides": {
                    "conversation_config_override": {
                        "agent": {
                            "first_message": True,
                            "language": True,
                            "prompt": {"prompt": True},
                        },
                        "tts": {
                            "voice_id": True,
                        },
                    }
                }
            }
        },
    )
    if resp.ok:
        print(f"    [agent] Overrides enabled for {agent_id}")
    else:
        print(f"    [agent] CRITICAL: Failed to enable overrides for {agent_id}: {resp.status_code} {resp.text}")
        print(f"    [agent] CRITICAL: Dial-in will NOT work for this agent without overrides!")


def _create_agent(client, style_key: str) -> str:
    """Create a single ElevenLabs Conversational AI agent for a style.

    Creates webhook tools and attaches them to the agent.
    Returns the new agent_id.
    """
    from elevenlabs.types import (
        AgentConfig,
        ConversationalConfig,
        PromptAgentApiModelOutput,
        TtsConversationalConfigOutput,
    )

    style = STYLES[style_key]
    char = STYLE_CHARACTERS[style_key]
    prompt = build_agent_prompt(style_key)
    lang = char["language"]
    # ElevenLabs requires different model families per language group:
    # English → eleven_turbo_v2, non-English → eleven_turbo_v2_5
    tts_model = "eleven_turbo_v2" if lang == "en" else "eleven_turbo_v2_5"

    # Create webhook tools first so we can attach them
    base_url = _get_base_url()
    print(f"    [agent] Webhook base URL: {base_url}")
    tool_ids = _create_tools(client, base_url)
    print(f"    [agent] Created {len(tool_ids)} tools")

    agent = client.conversational_ai.agents.create(
        name=f"{AGENT_NAME_PREFIX}{style_key}",
        conversation_config=ConversationalConfig(
            agent=AgentConfig(
                prompt=PromptAgentApiModelOutput(
                    prompt=prompt,
                    llm="gpt-4o",
                    tool_ids=tool_ids,
                ),
                first_message=char["first_message"],
                language=lang,
            ),
            tts=TtsConversationalConfigOutput(
                voice_id=style["default_voice"],
                model_id=tts_model,
            ),
        ),
    )
    print(f"    [agent] Agent created: {agent.agent_id}")

    # Enable session-time overrides so the frontend can customize per style
    _enable_agent_overrides(client, agent.agent_id)

    return agent.agent_id


def ensure_agents() -> dict:
    """Discover existing RetroCast agents and create any that are missing.

    Returns {style_key: agent_id} for all styles that have agents.
    Results are cached for the lifetime of the process.
    """
    global _agents_cache
    if _agents_cache:
        return _agents_cache

    from elevenlabs import ElevenLabs

    client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])

    # Discover existing agents by name prefix
    response = client.conversational_ai.agents.list()
    agents = response.agents if hasattr(response, "agents") else []

    found = {}
    for a in agents:
        if a.name and a.name.startswith(AGENT_NAME_PREFIX):
            key = a.name[len(AGENT_NAME_PREFIX):]
            if key in STYLES:
                found[key] = a.agent_id

    # Create missing agents
    for style_key in STYLES:
        if style_key not in found:
            print(f"  Creating agent {AGENT_NAME_PREFIX}{style_key}...")
            found[style_key] = _create_agent(client, style_key)
            print(f"    -> {found[style_key]}")

    # Ensure existing agents have tools attached
    base_url = _get_base_url()
    print(f"  [ensure] base_url = {base_url!r}")
    print(f"  [ensure] Found {len(found)} agents: {list(found.keys())}")
    for style_key, agent_id in found.items():
        try:
            agent_detail = client.conversational_ai.agents.get(agent_id=agent_id)
            prompt_cfg = agent_detail.conversation_config.agent.prompt
            tool_ids = prompt_cfg.tool_ids if prompt_cfg else None
            from elevenlabs.types import (
                AgentConfig,
                ConversationalConfig,
                PromptAgentApiModelOutput,
            )
            if not tool_ids:
                print(f"  [ensure] Agent {style_key} ({agent_id}) has no tools — adding...")
                new_tool_ids = _create_tools(client, base_url)
                client.conversational_ai.agents.update(
                    agent_id=agent_id,
                    conversation_config=ConversationalConfig(
                        agent=AgentConfig(
                            prompt=PromptAgentApiModelOutput(
                                prompt=prompt_cfg.prompt if prompt_cfg else "",
                                llm=prompt_cfg.llm if prompt_cfg else "gpt-4o",
                                tool_ids=new_tool_ids,
                            ),
                        ),
                    ),
                )
                print(f"  [ensure] Added {len(new_tool_ids)} tools to {style_key}")
            else:
                # Verify tool URLs match current base_url
                try:
                    first_tool = client.conversational_ai.tools.get(tool_id=tool_ids[0])
                    tool_url = ""
                    if hasattr(first_tool, 'tool_config') and hasattr(first_tool.tool_config, 'api_schema'):
                        tool_url = getattr(first_tool.tool_config.api_schema, 'url', "") or ""
                    expected_prefix = f"{base_url}/api/agent/tools/"
                    print(f"  [ensure] Agent {style_key} — checking tool URLs...")
                    print(f"           Tool[0] ID: {tool_ids[0]}")
                    print(f"           Tool[0] URL: {tool_url!r}")
                    print(f"           Expected prefix: {expected_prefix!r}")
                    if expected_prefix not in tool_url:
                        print(f"  [ensure] Agent {style_key} — URL MISMATCH, recreating tools...")
                        # Delete old tools
                        for tid in tool_ids:
                            try:
                                client.conversational_ai.tools.delete(tool_id=tid)
                                print(f"           Deleted old tool {tid}")
                            except Exception as del_e:
                                print(f"           Failed to delete tool {tid}: {del_e}")
                        # Create new tools with correct URL
                        new_tool_ids = _create_tools(client, base_url)
                        client.conversational_ai.agents.update(
                            agent_id=agent_id,
                            conversation_config=ConversationalConfig(
                                agent=AgentConfig(
                                    prompt=PromptAgentApiModelOutput(
                                        prompt=prompt_cfg.prompt if prompt_cfg else "",
                                        llm=prompt_cfg.llm if prompt_cfg else "gpt-4o",
                                        tool_ids=new_tool_ids,
                                    ),
                                ),
                            ),
                        )
                        print(f"  [ensure] Recreated {len(new_tool_ids)} tools for {style_key}")
                    else:
                        print(f"  [ensure] Agent {style_key} — {len(tool_ids)} tools OK (URLs match)")
                except Exception as e:
                    print(f"  [ensure] Could not verify tool URLs for {style_key}: {e}")
                    import traceback
                    traceback.print_exc()
                    print(f"  [ensure] Agent {style_key} — {len(tool_ids)} tools (UNVERIFIED)")
            # Ensure overrides are enabled (idempotent — re-enabling is a no-op)
            _enable_agent_overrides(client, agent_id)
        except Exception as e:
            print(f"  [ensure] WARNING checking agent {style_key}: {e}")

    _agents_cache = found
    return found


def get_agent_id(style_key: str) -> str | None:
    """Get the agent_id for a broadcast style.

    Calls ensure_agents() on first use (discovers + creates missing agents).
    Returns None if the style is unknown.
    """
    if style_key not in STYLES:
        return None
    agents = ensure_agents()
    return agents.get(style_key)





# ---------------------------------------------------------------------------
# Agent configuration (one-time setup for the pre-created agent)
# ---------------------------------------------------------------------------

# Base prompt used when no per-style override is active
BASE_AGENT_PROMPT = """\
You are a news anchor on RetroCast, a retro news broadcast service. You host a \
live call-in segment where listeners can ask questions about the news or seek advice.

CALL-IN FLOW:
1. Greet the listener and ask for their name.
2. Acknowledge their name warmly: "Thank you, [NAME]. Please go ahead with your question."
3. Accept and handle their question.

QUESTION HANDLING:
For EVERY question:
- ALWAYS use the available tools (search_news, search_topic, or read_article) to research \
and ground your response in real, current facts. Never answer from memory alone.

For NEWS-RELATED questions:
- FIRST use the fact_check tool to verify whether the news is real or misleading.
- Cross-reference with multiple sources before responding.
- If the news appears misleading or unverified, say so clearly but gently.

For ADVICE or HELP questions:
- Use search_topic or search_news to find factual grounding.
- Be warm, thoughtful, non-judgmental.

ANSWER STYLE:
- Warm, calm, thoughtful, non-judgmental
- Stay in character as a broadcast news anchor
- ALWAYS use tools for factual grounding — this is mandatory
- Keep responses concise but informative (2-4 sentences)

TODAY'S BROADCAST CONTEXT:
{{broadcast_context}}
"""


def configure_agent_webhooks(base_url: str, agent_id: str = ""):
    """Update an agent with webhook tools.

    Run this once after deploying the server (or when the base URL changes).
    Per-style customization (voice, language, prompt) happens via overrides at session start.

    Tools are created as standalone resources, then linked to the agent via tool_ids.

    Args:
        base_url: Public URL where the Flask server is reachable.
        agent_id: The agent to configure.
    """
    from elevenlabs import ElevenLabs
    from elevenlabs.types import (
        AgentConfig,
        ConversationalConfig,
        PromptAgentApiModelOutput,
        ToolRequestModel,
        ToolRequestModelToolConfig_Webhook,
        TtsConversationalConfigOutput,
        WebhookToolApiSchemaConfigInput,
    )

    if not agent_id:
        print("ERROR: No agent ID provided.")
        return

    client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])

    # First, fetch current agent to show what we're updating
    print(f"Fetching agent {agent_id}...")
    current = client.conversational_ai.agents.get(agent_id=agent_id)
    print(f"  Name: {current.name}")
    print(f"  Agent ID: {current.agent_id}")

    # Check for existing tools and clean up
    existing_tool_ids = current.conversation_config.agent.prompt.tool_ids or []
    if existing_tool_ids:
        print(f"\nRemoving {len(existing_tool_ids)} existing tools...")
        for tid in existing_tool_ids:
            try:
                client.conversational_ai.tools.delete(tool_id=tid)
                print(f"  Deleted tool {tid}")
            except Exception as e:
                print(f"  Could not delete tool {tid}: {e}")

    # Define our 4 webhook tools
    secret = os.environ.get("AGENT_WEBHOOK_SECRET", "")

    tool_defs = [
        {
            "name": "search_news",
            "description": "Search for recent news articles on a topic. Use this to find current news stories.",
            "properties": {
                "query": {"type": "string", "description": "Search query for news articles"},
                "region": {"type": "string", "description": "Optional region filter (e.g., 'India', 'UK', 'US', 'Brazil')"},
            },
            "required": ["query"],
        },
        {
            "name": "fact_check",
            "description": "Verify a news claim by searching for fact-checks and corroborating sources. Use this when a user mentions news that needs verification.",
            "properties": {
                "claim": {"type": "string", "description": "The news claim to verify"},
                "context": {"type": "string", "description": "Optional additional context about the claim"},
            },
            "required": ["claim"],
        },
        {
            "name": "read_article",
            "description": "Read the full content of a news article given its URL. Use this to get detailed information from a specific source.",
            "properties": {
                "url": {"type": "string", "description": "The URL of the article to read"},
            },
            "required": ["url"],
        },
        {
            "name": "search_topic",
            "description": "Search the web for information on any topic. Use this for general knowledge queries, advice questions, or background research.",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
    ]

    # Create each tool and collect IDs
    tool_ids = []
    print(f"\nCreating {len(tool_defs)} webhook tools:")
    for td in tool_defs:
        url = f"{base_url}/api/agent/tools/{td['name']}"
        print(f"  Creating {td['name']} -> {url}")

        tool_response = client.conversational_ai.tools.create(
            request=ToolRequestModel(
                tool_config=ToolRequestModelToolConfig_Webhook(
                    type="webhook",
                    name=td["name"],
                    description=td["description"],
                    api_schema=WebhookToolApiSchemaConfigInput(
                        url=url,
                        method="POST",
                        request_headers={
                            "X-Agent-Secret": secret,
                        } if secret else {},
                        request_body_schema={
                            "type": "object",
                            "properties": td["properties"],
                            "required": td["required"],
                        },
                    ),
                ),
            ),
        )
        tool_ids.append(tool_response.id)
        print(f"    Created: {tool_response.id}")

    # Default voice (BBC — good English default; overridden per style)
    default_voice = STYLES["bbc"]["default_voice"]

    # Update the agent with tools and config
    print(f"\nUpdating agent with {len(tool_ids)} tools...")
    client.conversational_ai.agents.update(
        agent_id=agent_id,
        name="RetroCast Anchor",
        conversation_config=ConversationalConfig(
            agent=AgentConfig(
                prompt=PromptAgentApiModelOutput(
                    prompt=BASE_AGENT_PROMPT,
                    llm="gpt-4o",
                    tool_ids=tool_ids,
                ),
                first_message=(
                    "Good evening. The broadcast is concluded. "
                    "You're welcome to ask about any of today's stories. "
                    "May I know your name?"
                ),
                language="en",
            ),
            tts=TtsConversationalConfigOutput(
                voice_id=default_voice,
                model_id="eleven_v3_conversational",
            ),
        ),
    )
    print(f"\nAgent {agent_id} configured successfully!")
    print(f"Webhook base URL: {base_url}")
    print(f"Tools: {', '.join(td['name'] for td in tool_defs)}")
    print(f"Tool IDs: {tool_ids}")


def show_agent_info():
    """Show the current configuration of all RetroCast agents."""
    from elevenlabs import ElevenLabs

    agents = ensure_agents()
    if not agents:
        print("No RetroCast agents found.")
        return

    client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])

    for style_key, agent_id in sorted(agents.items()):
        agent = client.conversational_ai.agents.get(agent_id=agent_id)
        print(f"\n{'='*50}")
        print(f"Agent: {agent.name}")
        print(f"ID: {agent.agent_id}")

        cc = agent.conversation_config
        if cc and cc.agent:
            a = cc.agent
            print(f"\nLanguage: {a.language}")
            print(f"First message: {a.first_message}")
            if a.prompt:
                print(f"LLM: {a.prompt.llm}")
                prompt_preview = (a.prompt.prompt or "")[:200]
                print(f"Prompt: {prompt_preview}...")
                tools = a.prompt.tools or []
                print(f"\nTools ({len(tools)}):")
                for t in tools:
                    name = getattr(t, "name", "unknown")
                    ttype = getattr(t, "type", "unknown")
                    print(f"  - {name} ({ttype})")

        if cc and cc.tts:
            print(f"\nTTS voice: {cc.tts.voice_id}")
            print(f"TTS model: {cc.tts.model_id}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "configure":
        if len(sys.argv) < 3:
            print("Usage: python agent_config.py configure <BASE_URL>")
            print("Example: python agent_config.py configure https://abc123.ngrok.io")
            sys.exit(1)
        base_url = sys.argv[2].rstrip("/")
        agents = ensure_agents()
        for style_key, agent_id in sorted(agents.items()):
            print(f"\nConfiguring webhooks for {AGENT_NAME_PREFIX}{style_key}...")
            configure_agent_webhooks(base_url, agent_id=agent_id)

    elif cmd == "info":
        show_agent_info()

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)
