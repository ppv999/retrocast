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


def build_agent_prompt(style_key: str, broadcast_context: str = "") -> str:
    """Construct the conversational system prompt for a RetroCast anchor agent."""
    char = STYLE_CHARACTERS[style_key]

    tool_filler = char.get("tool_filler", "One moment...")

    prompt = f"""{char["character"]}

You are the anchor of RetroCast, a retro news broadcast. After delivering today's news,
you now host a live call-in segment where listeners can ask questions.

CALL-IN FLOW:
When the listener initiates conversation:
1. Ask: "You are live on RetroCast. May I know your name?" (in your language/character)
2. Wait for their response.
3. Respond warmly, acknowledging their name: "Thank you, [NAME]. Please go ahead with your question."
4. Accept and handle their question.

TOOL USAGE BEHAVIOR:
- You have research tools, but the listener must NEVER know they exist.
- Never say "let me search", "I'll look that up", "checking my database", or anything
  that reveals you are using tools, search engines, or databases.
- Instead, when you need a moment, use your in-character filler phrase:
  "{tool_filler}"
- After receiving tool results, present the information as if it came from your own
  newsroom knowledge, correspondents, or editorial team.

NEWS QUERY RULES:
- For ANY question about current events, headlines, or "what's happening", ALWAYS use
  search_news first. Include the region parameter matching your broadcast's country.
- If the listener asks a general question without specifying a topic, default to
  today's top news for your region.
- Only broaden to search_topic for niche, specific, or non-news topics (e.g., "how
  does a vaccine work?", "tell me about the history of...").
- Your answers must be grounded in today's specific events, not general knowledge
  about a country.

FACT-CHECKING:
- If the listener makes a claim, shares a rumor, or says "I heard that...",
  ALWAYS use the fact_check tool before answering.
- Cross-reference with multiple sources before responding.
- If the news appears misleading or unverified, say so clearly but gently, in character.

ANSWER STYLE:
- Warm, calm, thoughtful, non-judgmental
- Structured responses — avoid pure opinions unless framed carefully
- Stay in character — do not break the retro persona
- ALWAYS use tools for factual grounding — this is mandatory
- Keep responses concise but informative (2-4 sentences for most answers)

If the user's question naturally connects to a useful resource or tool, you may include
a brief, neutral mention (1 line max). Do NOT sound like an advertisement.

TODAY'S BROADCAST CONTEXT:
{{{{broadcast_context}}}}
"""
    return prompt


def get_style_overrides(style_key: str, broadcast_context: str = "") -> dict:
    """Return per-style overrides to customize the base agent for each broadcast style.

    These overrides are passed to the ElevenLabs Conversation SDK's startSession()
    to dynamically change voice, prompt, language, and first message per style.

    The prompt override is kept short (character + instructions only).
    Broadcast context is passed as a dynamic variable to avoid oversized payloads.
    """
    style = STYLES[style_key]
    char = STYLE_CHARACTERS[style_key]

    # Build prompt WITHOUT broadcast context (keep it short for overrides)
    prompt = build_agent_prompt(style_key, broadcast_context="")

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


def get_dynamic_variables(style_key: str, broadcast_context: str = "") -> dict:
    """Return dynamic variables for the conversation session.

    Broadcast context (today's script + articles) is passed here
    to keep the overrides payload small.
    """
    # Truncate broadcast context to avoid oversized payloads
    if len(broadcast_context) > 2000:
        broadcast_context = broadcast_context[:2000] + "\n[truncated]"

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
    """Determine the public base URL for webhook callbacks."""
    # Explicit override first
    base = os.environ.get("AGENT_BASE_URL", "")
    if base:
        return base.rstrip("/")
    # Auto-detect from Replit environment
    domain = os.environ.get("REPLIT_DOMAINS", "")
    if domain:
        # REPLIT_DOMAINS can be comma-separated; use the first one
        return f"https://{domain.split(',')[0].strip()}"
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
                        } if secret else None,
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
    for style_key, agent_id in found.items():
        try:
            agent_detail = client.conversational_ai.agents.get(agent_id=agent_id)
            prompt_cfg = agent_detail.conversation_config.agent.prompt
            tool_ids = prompt_cfg.tool_ids if prompt_cfg else None
            if not tool_ids:
                print(f"  [ensure] Agent {style_key} ({agent_id}) has no tools — adding...")
                new_tool_ids = _create_tools(client, base_url)
                from elevenlabs.types import (
                    AgentConfig,
                    ConversationalConfig,
                    PromptAgentApiModelOutput,
                )
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
                print(f"  [ensure] Agent {style_key} — {len(tool_ids)} tools OK")
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


def build_tool_definitions(base_url: str) -> list:
    """Build webhook tool definitions for the agent, pointing to Flask endpoints.

    These are used when creating new agents programmatically via the SDK.
    """
    from elevenlabs.types import (
        PromptAgentApiModelInputToolsItem_Webhook,
        WebhookToolApiSchemaConfigInput,
    )

    secret = os.environ.get("AGENT_WEBHOOK_SECRET", "")

    def _make_tool(name, description, properties, required):
        return PromptAgentApiModelInputToolsItem_Webhook(
            type="webhook",
            name=name,
            description=description,
            api_schema=WebhookToolApiSchemaConfigInput(
                url=f"{base_url}/api/agent/tools/{name}",
                method="POST",
                request_headers={
                    "X-Agent-Secret": secret,
                } if secret else None,
                request_body_schema={
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            ),
        )

    return [
        _make_tool(
            "search_news",
            "Search for recent news articles on a topic. Use this to find current news stories.",
            {
                "query": {
                    "type": "string",
                    "description": "Search query for news articles",
                },
                "region": {
                    "type": "string",
                    "description": "Optional region filter (e.g., 'India', 'UK', 'US', 'Brazil')",
                },
            },
            ["query"],
        ),
        _make_tool(
            "fact_check",
            "Verify a news claim by searching for fact-checks and corroborating sources. "
            "Use this when a user mentions news that needs verification.",
            {
                "claim": {
                    "type": "string",
                    "description": "The news claim to verify",
                },
                "context": {
                    "type": "string",
                    "description": "Optional additional context about the claim",
                },
            },
            ["claim"],
        ),
        _make_tool(
            "read_article",
            "Read the full content of a news article given its URL. "
            "Use this to get detailed information from a specific source.",
            {
                "url": {
                    "type": "string",
                    "description": "The URL of the article to read",
                },
            },
            ["url"],
        ),
        _make_tool(
            "search_topic",
            "Search the web for information on any topic. "
            "Use this for general knowledge queries, advice questions, or background research.",
            {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
            },
            ["query"],
        ),
    ]




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


def _build_output_tools(base_url: str) -> list:
    """Build webhook tool definitions using Output types (for agent update)."""
    from elevenlabs.types import (
        PromptAgentApiModelOutputToolsItem_Webhook,
        WebhookToolApiSchemaConfigOutput,
    )

    secret = os.environ.get("AGENT_WEBHOOK_SECRET", "")

    def _make_tool(name, description, properties, required):
        return PromptAgentApiModelOutputToolsItem_Webhook(
            type="webhook",
            name=name,
            description=description,
            api_schema=WebhookToolApiSchemaConfigOutput(
                url=f"{base_url}/api/agent/tools/{name}",
                method="POST",
                request_headers={
                    "X-Agent-Secret": secret,
                } if secret else None,
                request_body_schema={
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            ),
        )

    return [
        _make_tool(
            "search_news",
            "Search for recent news articles on a topic. Use this to find current news stories.",
            {
                "query": {
                    "type": "string",
                    "description": "Search query for news articles",
                },
                "region": {
                    "type": "string",
                    "description": "Optional region filter (e.g., 'India', 'UK', 'US', 'Brazil')",
                },
            },
            ["query"],
        ),
        _make_tool(
            "fact_check",
            "Verify a news claim by searching for fact-checks and corroborating sources. "
            "Use this when a user mentions news that needs verification.",
            {
                "claim": {
                    "type": "string",
                    "description": "The news claim to verify",
                },
                "context": {
                    "type": "string",
                    "description": "Optional additional context about the claim",
                },
            },
            ["claim"],
        ),
        _make_tool(
            "read_article",
            "Read the full content of a news article given its URL. "
            "Use this to get detailed information from a specific source.",
            {
                "url": {
                    "type": "string",
                    "description": "The URL of the article to read",
                },
            },
            ["url"],
        ),
        _make_tool(
            "search_topic",
            "Search the web for information on any topic. "
            "Use this for general knowledge queries, advice questions, or background research.",
            {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
            },
            ["query"],
        ),
    ]


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
                        } if secret else None,
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
