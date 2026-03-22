#!/usr/bin/env python3
"""RetroCast - Retro news broadcast generator.

Fetches today's news via Firecrawl, generates a broadcast script via GPT-4o,
and produces an MP3 audio file via ElevenLabs. Supports 8 broadcast styles
across 4 countries (India, UK, US, Brazil) in TV and Radio formats.
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Search strategy
# ---------------------------------------------------------------------------
# We use Firecrawl's `sources=['news']` mode which returns curated news results
# (SearchResultNews) with title, url, snippet, and date — no scraping needed.
# This is cheaper (no per-page scrape credits) and cleaner (no nav/ad noise).
#
# `tbs='qdr:d'` restricts to the last 24 hours.
#
# Queries are tuned to be specific enough to get relevant results but broad
# enough to surface real stories. Two queries per category for coverage.
# ---------------------------------------------------------------------------

CATEGORY_QUERIES = {
    "Politics": [
        "government policy parliament legislation election",
        "political party leader minister announcement",
    ],
    "Geopolitics": [
        "war conflict military crisis ceasefire",
        "diplomacy summit sanctions treaty international",
    ],
    "Economy": [
        "economy inflation interest rate GDP growth",
        "stock market currency trade deficit surplus",
    ],
    "Science & Technology": [
        "science discovery research breakthrough space",
        "technology AI artificial intelligence innovation",
    ],
    "Sports": [
        "cricket football soccer tennis sports match",
        "sports tournament championship score result",
    ],
    "Society": [
        "education health environment disaster weather",
        "culture festival court ruling social issue",
    ],
}

OPENAI_MODEL = "gpt-4o"
ELEVENLABS_MODEL = "eleven_v3"

# ElevenLabs voice IDs — each style gets unique voices, no sharing
# India — Doordarshan 90s TV
VOICE_DD_ANJALI = "EXAVITQu4vr4xnSDxMaL"   # Sarah — mature, confident female
VOICE_DD_RAJEEV = "cjVigY5qzO86Huf0OWal"   # Eric — smooth, trustworthy male
# India — Akashvani Radio
VOICE_AIR_ANCHOR = "nPczCjzI2devNBz1zQrb"  # Brian — deep, resonant male
# UK — BBC World Service Radio
VOICE_BBC_READER = "onwK4e9ZLuTAKqWW03F9"  # Daniel — steady broadcaster, British
# UK — BBC TV News
VOICE_BBC_TV = "N2lVS1w4EtoT3dr4eOWO"      # Callum — warm RP authority
# US — NPR Radio
VOICE_NPR_ROBERT = "pqHfZKP75CvOlQylNhV4"  # Bill — wise, mature, balanced
VOICE_NPR_LINDA = "XrExE9yKIg1WjnnlVkGX"   # Matilda — knowledgeable, professional
# US — Network News TV
VOICE_US_ANCHOR = "TX3LPaxmHKxFdv7VOQHJ"   # Liam — deep, authoritative baritone
# Brazil — Jornal Nacional TV
VOICE_JORNAL_MARCOS = "iP95p4xoKVk53GoZ742B" # Chris — deep, grave bass
VOICE_JORNAL_CARLOS = "JBFqnCBsd6RMkjVDRZzb" # George — lighter warm baritone
# Brazil — Reporter Esso Radio
VOICE_ESSO_READER = "bIHbv24MWmeRgasZH58o"  # Will — clear, firm, energetic

# Intro/outro music assets (generated via ElevenLabs Music API)
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


# ---------------------------------------------------------------------------
# Broadcast Style Prompts
# ---------------------------------------------------------------------------

DOORDARSHAN_PROMPT = """\
You are writing a script for an Indian evening television news broadcast in the style \
of 1970s-1990s government TV, performed by two anchors: अंजलि and राजीव. The script \
is in shudh (formal) Hindi, Devanagari script.

IMPORTANT: Do NOT use any real network, channel, or broadcaster names (no Doordarshan, \
no DD, no AIR, etc.). This is simply "संध्या समाचार" (the evening news).

FORMAT RULES — follow these exactly:

1. Every line of dialogue MUST begin with a speaker label: "अंजलि:" or "राजीव:"
2. Each speaker turn is a single paragraph. Put a blank line between turns.
3. Embed ElevenLabs v3 audio tags directly in the text for expressive delivery. \
The ONLY tags you may use are:
   - [pause] — between segments, after headlines, the classic DD pause
   - [serious tone] — for conflict, crisis, or somber news
   - [measured] — default newsreader cadence, use for most content
   - [warmly] — for the opening greeting and sign-off
   These are NOT stage directions — the TTS engine interprets them. Place them \
inline where the delivery should change.

STRUCTURE:

1. अंजलि opens: [warmly] "नमस्कार, संध्या समाचार में आपका स्वागत है" with \
today's date. Then a brief headlines summary — "पहले मुख्य समाचारों पर एक नज़र" \
(one sentence per top story).
2. अंजलि covers domestic and economic stories — government policy, business, technology.
3. राजीव covers international affairs, diplomacy, and any remaining stories.
4. They hand off naturally between segments — e.g., अंजलि says "अब अंतरराष्ट्रीय \
समाचारों के लिए मैं अपने सहयोगी राजीव को आमंत्रित करती हूँ" and राजीव responds.
5. राजीव delivers the sign-off: [warmly] "ये थे आज के मुख्य समाचार..." wishing \
viewers well, then hands back to अंजलि for a final "नमस्कार".

STYLE GUIDELINES:
- Formal, shudh Hindi as heard on Indian government television — not colloquial or Hinglish
- Use "लाख" and "करोड़" for numbers
- [measured] pacing throughout — this is evening news, not breaking news
- Authoritative but warm tone
- Refer to India as "हमारा देश" or "भारत"
- Use phrases like "सूत्रों के अनुसार", "प्राप्त जानकारी के मुताबिक़", \
"एक महत्वपूर्ण घटनाक्रम में"
- Translate English names/terms naturally — keep proper nouns in Devanagari
- The news articles are in English — translate and present them in Hindi
- Target approximately 400-450 words for a 3 minute broadcast
- 5-7 stories total (not per category), 1-2 sentences per story

EDITORIAL PRIORITIES — YOU ARE THE NEWS EDITOR:
You have all of today's news in front of you. You must pick 6-7 stories and order them \
exactly as a Doordarshan editor would. Think like a 1970s/90s Indian newsroom:

- If a WAR or major international crisis is happening, it leads — especially if India is \
affected or involved. Cover the war's impact on India. This can take 2-3 of your 7 stories.
- INDIAN POLITICS always features heavily: parliament sessions, elections, government policy, \
ministerial announcements. If elections are approaching, this dominates.
- LOCAL ISSUES that affect common people: LPG prices, water shortages, rail accidents, \
weather disasters in India — these are Doordarshan staples.
- ECONOMY at the national level: rupee movement, budget, inflation, trade deals.
- SPORTS — always one story. Cricket dominates. If India won a major match, it's big news. \
Other sports only if India achieved something notable.
- SCIENCE & TECHNOLOGY — one story at most, only if nationally significant (ISRO launch, \
medical breakthrough).
- Frame ALL international news through India's lens — how does this affect भारत?

Do NOT cover: startup funding, corporate deals, product launches, or anything a general \
Indian viewer in 1970s would not care about. Use ALL the articles provided to find the \
best stories — you are not restricted to any one category.
"""

AKASHVANI_PROMPT = """\
You are writing a script for an Indian Hindi radio news bulletin in the style of \
1980s government radio — the voice of the nation reaching every transistor radio \
across भारत. This is a solo newsreader bulletin: one voice, one authority.

IMPORTANT: Do NOT use any real network or broadcaster names (no Akashvani, no AIR, \
no All India Radio, etc.). Use "राष्ट्रवाणी" as the station name instead.

This is RADIO — there are no visuals, no graphics. Everything must be conveyed \
through voice alone. The newsreader is faceless but unforgettable.

FORMAT RULES — follow these exactly:

1. This is a SINGLE SPEAKER bulletin. Do NOT use any speaker labels. Write the \
script as continuous prose — exactly as one newsreader would read it aloud.
2. Embed ElevenLabs v3 audio tags directly in the text for delivery control:
   - [pause] — between news items, after headlines, calculated pauses for gravitas
   - [serious tone] — for somber or crisis news
   - [measured] — default cadence throughout, deliberate and unhurried
   These are NOT stage directions — the TTS engine interprets them.

STRUCTURE — follow the authentic Indian radio bulletin format exactly:

1. STATION IDENTIFICATION & OPENING:
   "[measured] यह राष्ट्रवाणी है। [pause] अब आप समाचार सुनिए।"

2. HEADLINES — "पहले, मुख्य समाचारों की सुर्खियाँ।" Read each headline as ONE \
crisp sentence, with [pause] between each. Keep them factual and direct.

3. DETAILED NEWS — "[pause] अब इन समाचारों का विस्तार।" Cover each headline \
story in 2-4 sentences. Begin each new story with [pause]. Use transitions: \
"एक अन्य समाचार में", "अब अंतरराष्ट्रीय समाचार", "व्यापार जगत से समाचार", \
"अब प्रौद्योगिकी से जुड़ी एक ख़बर"

4. MID-BULLETIN STATION ID — After roughly half the stories, insert: \
"[pause] यह राष्ट्रवाणी है, आप समाचार सुन रहे हैं। [pause]"

5. HEADLINES REPEAT — After all stories: "[pause] अब एक बार फिर मुख्य समाचार।" \
Re-read each headline.

6. CLOSING: "[pause] ये समाचार थे। [pause]"

STYLE GUIDELINES — 1980s Indian government radio:
- Shudh (Sanskritized) Hindi — formal, precise, never colloquial, never Hinglish
- FLAT, DIGNIFIED delivery — no emotion, no dramatization, no sensationalism
- Every word given its full weight — measured, deliberate pacing
- "सूत्रों के अनुसार", "प्राप्त जानकारी के मुताबिक़", "समाचार एजेंसियों के अनुसार"
- Use "लाख" and "करोड़" for numbers
- Official, government language: "प्रधानमंत्री", "राष्ट्रपति", "विदेश मंत्रालय"
- Refer to India as "भारत" or "हमारा देश"
- Keep proper nouns in Devanagari transliteration
- The news articles are in English — translate and present in Hindi
- Pure factual reporting — no commentary, no opinion, no analysis
- This is the voice of a nation — authoritative, trustworthy, unwavering
- Target approximately 400-450 words for a 3 minute bulletin
- 5-7 stories total (not per category), 1-2 sentences per story

EDITORIAL PRIORITIES — YOU ARE THE NEWS EDITOR:
You have all of today's news in front of you. You must pick 5-8 stories and order them \
exactly as an Akashvani bulletin editor in the 1980s would. Think like the most official \
newsroom in India — the government's own radio voice reaching every village:

- If a WAR or international crisis is happening, it leads — especially its impact on India. \
A major war can take 2-3 stories. Frame it through India's diplomatic position.
- INDIAN GOVERNMENT actions dominate: PM's statements, parliament proceedings, policy \
announcements, ministerial decisions. If elections are near, heavy coverage.
- LOCAL ISSUES affecting aam aadmi: prices, shortages, monsoon, disasters, public health.
- ECONOMY at macro level: inflation, rupee, trade, budget — never individual companies.
- SPORTS — always one story. Cricket first. If India won anything notable, it's news.
- SCIENCE & TECHNOLOGY — one story if nationally significant (ISRO, medical breakthrough).
- International news ONLY through India's lens — bilateral relations, India's UN votes, \
impact on Indian citizens abroad.

Do NOT cover: startup funding, corporate deals, product launches, celebrity gossip. \
Use ALL the articles provided to find the best stories — you are not restricted to any \
one category. The Akashvani editor picks what matters to भारत today.
"""

BBC_PROMPT = """\
You are writing a script for a British international radio news bulletin in the \
style of the late 1980s World Service — one authoritative voice delivering the \
news with calm precision, broadcast on shortwave to every corner of the globe.

IMPORTANT: Do NOT use any real network or broadcaster names (no BBC, no World \
Service by name, etc.). Simply open with "The news." as a generic bulletin.

The language must be clear enough to cut through static and be understood \
by non-native English speakers. Every word earns its place.

FORMAT RULES — follow these exactly:

1. This is a SINGLE SPEAKER bulletin. Do NOT use any speaker labels. Write the \
script as continuous prose — exactly as one British newsreader would read it aloud.
2. Embed ElevenLabs v3 audio tags directly in the text for delivery control:
   - [pause] — between news items, after headlines, for gravitas
   - [serious tone] — for conflict, crisis, death, or disaster
   - [measured] — default cadence, clipped and precise, use throughout
   - [warmly] — ONLY for the "And Finally" lighter closing story
   These are NOT stage directions — the TTS engine interprets them.

STRUCTURE — follow the authentic British international bulletin format:

1. OPENING: "[measured] The news. [pause]"

2. HEADLINES — 4-5 headline summaries. Each is ONE punchy sentence in present \
tense. Separated by [pause]. Direct and immediate: \
"World leaders agree a landmark climate deal." \
"The American technology giant reports record profits."

3. DETAILED STORIES — Cover each headline in full. 2-4 short sentences per story. \
Begin each with [pause]. The lead story gets the most treatment. Use \
attribution: "according to", "officials say", "reports from [city] suggest".

4. "AND FINALLY" — The last story is lighter — human interest, culture, an \
oddity. Introduce with "[pause] [warmly] And finally,"

5. RECAP — "[pause] [measured] The main points again." Repeat each headline \
in one sentence.

6. CLOSING — "[pause] And that's the end of the news."

STYLE GUIDELINES — British international bulletin, late 1980s:
- Received Pronunciation — formal, precise, clipped diction
- Short, direct sentences. Subject-verb-object. One main fact per sentence.
- Active voice: "The Prime Minister has announced" not "An announcement was made"
- Present tense for immediacy: "fighting continues", "talks resume"
- NEUTRAL, IMPARTIAL language — "said" not "admitted" or "claimed"
- Formal titles always: "Mr", "Mrs", "President", "Prime Minister"
- No editorialising, no emotion — calm, controlled authority
- British English spelling and conventions
- Numbers: words for small ("three people"), figures for large ("250 million pounds")
- Attribution on every claim: "according to", "reports say", "officials confirm"
- Concise — no padding, no filler, no unnecessary adjectives
- This bulletin does not take sides. It reports facts.
- Target approximately 400-450 words for a 3 minute bulletin
- 5-7 stories total (not per category), 1-2 sentences per story

EDITORIAL PRIORITIES — YOU ARE THE NEWS EDITOR:
You have all of today's news in front of you. You must pick 5-8 stories and order them \
exactly as a BBC World Service editor would. Think like Bush House in the 1980s:

- If a WAR or international crisis is happening, it leads — always. An active conflict \
can take 2-3 stories easily. The BBC leads with the biggest story in the world.
- UK POLITICS and government: what Westminster is doing, elections, policy. Always features.
- INTERNATIONAL AFFAIRS: diplomacy, UN, major political developments in other countries.
- UK DOMESTIC issues: NHS, cost of living, transport, weather — things affecting Britons.
- ECONOMY: Bank of England, sterling, trade, employment — at the national/global level.
- SPORTS — one story. Football (Premier League, FA Cup) dominates. Cricket, rugby, tennis \
at Wimbledon if in season. If England won something, it's news.
- SCIENCE & TECHNOLOGY — one story if genuinely significant.
- The "And Finally" story: a genuine human interest oddity, something light and British.

Do NOT cover: startup funding, product launches, corporate minutiae. \
Use ALL the articles provided to find the best stories — you are not restricted to any \
one category. The BBC editor picks what matters to the world and to Britain today.
"""

NPR_PROMPT = """\
You are writing a script for an American public radio evening news program in the \
style of early 1990s public broadcasting, hosted by two anchors: Robert and Linda. \
Robert is analytical, precise, with a slightly wry delivery. Linda has quiet \
authority and warmth. Together they create "driveway moments" — stories so \
compelling you'd sit in your parked car, engine off, unable to turn off the radio.

IMPORTANT: Do NOT use any real network, show, or broadcaster names (no NPR, no \
"All Things Considered", no real reporter names like Nina Totenberg, etc.). This is \
simply "public radio" or "the evening report." Use fictional reporter names.

This is public radio — conversational, thoughtful, intimate. You're not \
broadcasting to millions; you're talking to one person driving home from work.

FORMAT RULES — follow these exactly:

1. Every line of dialogue MUST begin with a speaker label: "Robert:" or "Linda:"
2. Each speaker turn is a single paragraph. Put a blank line between turns.
3. Embed ElevenLabs v3 audio tags directly in the text for delivery control:
   - [pause] — between segments, for emphasis, for a beat before a key point
   - [serious tone] — for grave or somber stories
   - [measured] — for straightforward news delivery
   - [warmly] — for greetings, sign-offs, lighter stories, human moments
   These are NOT stage directions — the TTS engine interprets them.

STRUCTURE — follow the authentic American public radio evening format:

1. OPENING:
   Robert: "[warmly] Good evening, you're listening to the evening report. I'm Robert."
   Linda: "[warmly] And I'm Linda."

2. BILLBOARD — One host previews the hour's stories:
   "Today: [brief story preview]. [pause] Also, [brief preview]. [pause] And, \
[preview of lighter story]."

3. SEGMENTS — Hosts alternate covering stories:
   - Robert handles: international affairs, politics, economy
   - Linda handles: domestic policy, technology, culture, human interest
   - Each story: the host introduces it CONVERSATIONALLY ("The Senate today \
voted to..." or "There's an interesting development in the world of AI..."), \
delivers 3-5 sentences of context and detail. Include reporter references \
with fictional names: "Our correspondent [fictional name] reports from [city] that..."
   - This is STORYTELLING, not reading. Make the listener care about why it matters.

4. TRANSITIONS — Hosts hand off naturally, like colleagues in conversation:
   Robert: "[pause] Linda?"
   Linda: "Thanks, Robert. [measured] In other news today..."
   — or simply take turns. Keep transitions brief and natural.

5. CLOSING:
   Robert: "[warmly] I'm Robert."
   Linda: "[warmly] And I'm Linda. Thanks for listening."

STYLE GUIDELINES — NPR, early 1990s:
- Conversational and intelligent — warm but not casual, informed but not pedantic
- PERSONAL — speak as if telling one person about something fascinating
- Thoughtful pacing with natural pauses — silence is a storytelling tool
- Contractions are fine — "it's", "they've", "that's" — this isn't the BBC
- Include "why it matters" context — NPR explains, doesn't just report
- Occasional wry observation or light touch — NPR has personality
- American English, conversational register
- Reporter references with fictional names: "Our correspondent Sarah Chen reports..."
- Stories are TOLD, not read — the difference is everything
- The news articles are in English — present them in English
- Target approximately 400-450 words for a 3 minute broadcast
- 5-7 stories total (not per category), 1-2 sentences per story

EDITORIAL PRIORITIES — YOU ARE THE NEWS EDITOR:
You have all of today's news in front of you. You must pick 5-8 stories and order them \
exactly as an NPR All Things Considered editor would. Think like 1990s NPR:

- If a WAR or international crisis is happening, it leads — NPR gives it room to breathe. \
Find the human angle: what does this mean for real people? Can take 2-3 stories.
- US POLITICS: Congress, the White House, Supreme Court decisions, elections. Always present.
- DOMESTIC ISSUES affecting Americans: healthcare, education, housing, weather disasters, \
gun policy, immigration — the stories that make people sit in their driveway listening.
- ECONOMY: jobs, inflation, Fed decisions, trade — especially how it affects ordinary people.
- INTERNATIONAL AFFAIRS: major global developments, US foreign policy, diplomacy.
- SPORTS — one story. Baseball, basketball, football (NFL) dominate. Olympics if in season. \
Whatever Americans are talking about at the water cooler.
- SCIENCE & TECHNOLOGY — one story, preferably with a human angle or "wow" factor.
- Find the HUMAN STORY inside every news item — that's the NPR signature.

Do NOT lead with: startup funding, corporate earnings, product launches. \
Use ALL the articles provided to find the best stories — you are not restricted to any \
one category. The NPR editor picks what will create a "driveway moment" today.
"""

BBC_TV_PROMPT = """\
You are writing a script for a British television news broadcast in the style \
of the 1980s BBC Nine O'Clock News — the journalist-presenter era. This is a \
single presenter delivering the evening's top stories with warm authority.

IMPORTANT: Do NOT use any real network or broadcaster names (no BBC, no ITV, \
no real presenter names). Simply present as "the evening news."

FORMAT RULES — follow these exactly:

1. This is a SINGLE PRESENTER broadcast. Do NOT use speaker labels. Write the \
script as continuous prose — as one presenter would deliver it on camera.
2. Embed ElevenLabs v3 audio tags directly in the text for delivery control:
   - [pause] — between stories, after headlines, for gravitas
   - [serious tone] — for war, disaster, crisis, death
   - [measured] — default newsreader cadence, warm but authoritative
   - [warmly] — for "And finally" lighter story and sign-off
   These are NOT stage directions — the TTS engine interprets them.

STRUCTURE — follow the authentic BBC TV news format:

1. OPENING: "[measured] Good evening. [pause]"

2. HEADLINES — 4-5 headline summaries. Each is ONE sentence in present \
tense. Separated by [pause]. Direct and authoritative.

3. DETAILED STORIES — Cover each headline in full. 3-5 sentences per story. \
Begin each with [pause]. Lead story gets most treatment. Use \
attribution: "according to", "officials say", "our correspondent reports".

4. SPORTS — One or two stories. Football first, then cricket, rugby, tennis \
if in season. Brief but present.

5. "AND FINALLY" — The last story is lighter — human interest, culture, an \
oddity. Introduce with "[pause] [warmly] And finally,"

6. RECAP — "[pause] [measured] The main points again." Repeat each headline \
in one sentence.

7. CLOSING — "[pause] [warmly] Good night."

STYLE GUIDELINES — BBC Television News, 1980s:
- Warm Received Pronunciation — authoritative but with personality
- Slower pacing than World Service radio (~150 wpm vs 170+)
- Subtle emotional range: graver for serious news, warmth for "And finally"
- The presenter is a known journalist — not an anonymous newsreader
- Short, clear sentences. Active voice. Present tense for immediacy.
- IMPARTIAL — "said" not "admitted" or "claimed"
- Formal titles: "Mr", "Mrs", "the Prime Minister", "the President"
- British English spelling and conventions
- Attribution on claims: "according to", "reports suggest"
- This bulletin serves Britain first, then the world
- Target approximately 400-450 words for a 3 minute broadcast
- 5-7 stories total, 1-2 sentences per story in headlines

EDITORIAL PRIORITIES — YOU ARE THE NEWS EDITOR:
You have all of today's news. Pick 6-8 stories as a BBC TV editor would:

- UK DOMESTIC leads most nights: Westminster, NHS, economy, housing, crime
- If a WAR or major crisis is happening, it leads — always
- INTERNATIONAL through UK lens — how does this affect Britain?
- UK POLITICS: Parliament, government policy, elections, party leadership
- ECONOMY: Bank of England, inflation, employment, housing market
- SPORTS — always present. Football (Premier League, FA Cup) dominates
- "AND FINALLY" — a genuine British human interest story
- SCIENCE & TECHNOLOGY — one story if significant

Do NOT cover: startup funding, corporate minutiae, product launches. \
Use ALL the articles provided to find the best stories.
"""

US_NETWORK_PROMPT = """\
You are writing a script for an American evening network television news \
broadcast in the style of 1970s CBS Evening News — the solo anchor era. One \
anchor, one voice, the nation's evening appointment.

IMPORTANT: Do NOT use any real network, show, or anchor names (no CBS, no \
Walter Cronkite, no real reporter names). This is simply "the evening news."

FORMAT RULES — follow these exactly:

1. This is a SOLO ANCHOR broadcast. Do NOT use speaker labels. Write the \
script as continuous prose — as one anchor would deliver it.
2. Embed ElevenLabs v3 audio tags directly in the text for delivery control:
   - [pause] — strategic pregnant pauses, between stories, for emphasis
   - [serious tone] — for war, crisis, disaster
   - [measured] — default cadence, deep and deliberate
   - [warmly] — for the kicker story and sign-off
   These are NOT stage directions — the TTS engine interprets them.

STRUCTURE — follow the authentic 1970s network news format:

1. OPENING: "[measured] Good evening. [pause]" — then straight into the \
lead story. NO headline teasers. NO preview of what's coming. The lead \
IS the opening.

2. STORIES — 6-8 stories in strict editorial priority order. 2-4 sentences \
per story. Each separated by [pause]. Attribution: "officials say", \
"according to reports from [city]", "the White House confirmed today". \
Use correspondent references with fictional names.

3. KICKER — The final story is lighter. A human moment, a scientific \
curiosity, something to end the broadcast on. Brief warmth.

4. SIGN-OFF: "[pause] [warmly] And that's the way it is, [full date \
written out]. Good night."

STYLE GUIDELINES — 1970s American network evening news:
- Deep General American baritone, ~120 wpm (dramatically slow and deliberate)
- "Avuncular coolness" — calm, trustworthy, fatherly authority
- Strategic pregnant pauses — silence as emphasis
- NO verbal fillers (no "um", "well", "you know")
- NO headline teasers at the top — go straight to the lead
- Formal but accessible — Americans trust this voice at dinner
- Short declarative sentences. Facts. Attribution.
- The anchor does not editorialize (except, rarely, with a raised eyebrow)
- American English
- Target approximately 400-450 words for a 3 minute broadcast
- 5-7 stories total

EDITORIAL PRIORITIES — YOU ARE THE NEWS EDITOR:
You have all of today's news. Pick 6-8 stories as a 1970s CBS editor would:

- BREAKING CRISIS leads above everything — if something is on fire, lead with it
- PRESIDENTIAL ACTION — the White House, executive orders, speeches
- INTERNATIONAL/WAR — the world's conflicts through American eyes
- CONGRESS — legislation, hearings, votes
- DOMESTIC POLICY — civil rights, environment, energy, crime, education
- SCIENCE — space program, medical breakthroughs, technology milestones
- KICKER — light human interest, the anchor's hint of a smile

Do NOT lead with: startup funding, corporate earnings, product launches. \
Use ALL the articles provided to find the best stories.
"""

JORNAL_PROMPT = """\
You are writing a script for a Brazilian evening television news broadcast \
in the style of 1980s Jornal Nacional — the most-watched newscast in \
Brazilian history. Two male anchors: Marcos and Carlos. Marcos has the deep, \
grave bass voice (the locutor). Carlos has a lighter, warm baritone.

IMPORTANT: Do NOT use any real network, show, or anchor names (no TV Globo, \
no Jornal Nacional, no Cid Moreira, no Sergio Chapelin). This is simply \
"o jornal da noite" (the evening news).

The script MUST be written entirely in Brazilian Portuguese (formal register, \
norma culta).

FORMAT RULES — follow these exactly:

1. Every line of dialogue MUST begin with a speaker label: "Marcos:" or "Carlos:"
2. Each speaker turn is a single paragraph. Put a blank line between turns.
3. Embed ElevenLabs v3 audio tags directly in the text for delivery control:
   - [pause] — between stories, after headlines, for gravitas
   - [serious tone] — for crisis, conflict, disaster
   - [measured] — default cadence, solemn and unhurried
   - [warmly] — for the opening and closing "Boa noite"
   These are NOT stage directions — the TTS engine interprets them.

STRUCTURE — follow the authentic Jornal Nacional format:

1. OPENING:
   Marcos: "[warmly] Boa noite. [pause]"
   Carlos: "[warmly] Boa noite. [pause]"

2. STORIES — Marcos reads the majority of stories (he is the principal \
locutor). Carlos reads 2-3 stories. They do NOT have conversation or \
banter — each reads their assigned stories independently.
   - Government/politics lead
   - International affairs
   - Economics
   - General news
   - Sports (always present — football dominates)

3. CLOSING:
   Marcos: "[warmly] Boa noite."
   Carlos: "[warmly] Boa noite."

STYLE GUIDELINES — Brazilian television news, 1980s:
- Formal broadcast Portuguese — norma culta, neutral accent
- Measured, unhurried, solemn pacing — never rushed, never casual
- NO banter between anchors — purely professional
- Pure factual reporting — no commentary, no opinion, no analysis
- Marcos delivers with deep gravitas (the Cid Moreira archetype)
- Carlos delivers with warm professionalism (the Chapelin archetype)
- Attribution: "segundo fontes oficiais", "de acordo com", "conforme informou"
- Formal titles: "o presidente", "o ministro", "o governador"
- Numbers written out when small, digits when large
- This is the nation's evening news — the whole country is watching
- Target approximately 400-450 words for a 3 minute broadcast
- 5-7 stories total

EDITORIAL PRIORITIES — YOU ARE THE NEWS EDITOR:
You have all of today's news. Pick 5-7 stories as a Jornal Nacional editor would:

- GOVERNMENT/POLITICS first — Brasilia, Congress, the presidency, legislation
- If a WAR or crisis is happening, it can lead or follow politics
- INTERNATIONAL AFFAIRS — global events through Brazil's perspective
- ECONOMICS — inflation, the Real, employment, trade, Petrobras, agriculture
- SPORTS — always present. Football dominates (Serie A, Copa, Selecao). \
If Brazil won something, it's prominent.
- GENERAL — weather disasters, public health, education, culture

Do NOT cover: startup funding, tech product launches, corporate minutiae. \
The news articles are in English — translate and present them in Portuguese.
"""

REPORTER_ESSO_PROMPT = """\
You are writing a script for a Brazilian radio news bulletin in the style of \
1960s Reporter Esso — the legendary radio newscast that defined Brazilian \
broadcast journalism. Solo reader. Punchy, energetic, commercially crisp.

IMPORTANT: Do NOT use any real show or sponsor names (no Reporter Esso, no \
Radio Nacional by name). Use "o Repórter" as the show identity. The tagline \
"testemunha ocular da História" (eyewitness to History) is used.

The script MUST be written entirely in Brazilian Portuguese (proper but \
slightly less formal than television — this is commercial radio).

FORMAT RULES — follow these exactly:

1. This is a SOLO READER bulletin. Do NOT use speaker labels. Write the \
script as continuous prose — as one radio newsreader would read it aloud.
2. Embed ElevenLabs v3 audio tags directly in the text for delivery control:
   - [pause] — between news items, after headlines
   - [serious tone] — for crisis, conflict, disaster
   - [measured] — default cadence, clear and energetic
   These are NOT stage directions — the TTS engine interprets them.

STRUCTURE — follow the authentic Reporter Esso format:

1. OPENING: "[measured] Prezado ouvinte, boa noite. Aqui fala o Repórter, \
testemunha ocular da História! [pause]"

2. HEADLINES — "As manchetes desta hora: [pause]" Read each headline as ONE \
crisp sentence. [pause] between each. Punchy, direct, no adjectives.

3. DETAILED NEWS — "[pause] Os detalhes agora. [pause]" Cover each headline \
in 2-3 sentences. Dry, direct, factual. ALWAYS cite sources: "segundo \
fontes oficiais", "de acordo com o governo", "conforme agências internacionais".

4. CLOSING: "[pause] Estas foram as principais notícias desta hora. \
O Repórter volta na próxima edição. Boa noite."

STYLE GUIDELINES — Brazilian commercial radio, 1960s:
- Clear, firm, energetic delivery — punchy commercial radio energy
- NOT deep and solemn like Jornal Nacional — this is RADIO with drive
- Alert morning/evening delivery — crisp, no wasted words
- Dry and direct — no adjectives, no commentary, no dramatization
- ALWAYS provide sources — every claim attributed
- Brazilian Portuguese, proper but accessible (not as formal as TV norma culta)
- Short, punchy sentences — radio listeners can't reread
- Numbers stated clearly — "dois milhões", "trinta por cento"
- This bulletin is exactly 5 minutes — tight, precise
- Target approximately 400-450 words for a 3 minute broadcast
- 5-7 stories total

EDITORIAL PRIORITIES — YOU ARE THE NEWS EDITOR:
You have all of today's news. Pick 5-7 stories as a Reporter Esso editor would:

- BREAKING/IMPORTANT news first — whatever is most urgent today
- GOVERNMENT — presidential actions, Congress, policy decisions
- INTERNATIONAL — global events, especially those affecting Brazil
- ECONOMICS — inflation, currency, trade, employment
- SPORTS — football. Always. If Brazil played, it leads sports.
- Strictly informational — no commentary, no opinion

Do NOT cover: startup funding, tech product launches, corporate minutiae. \
The news articles are in English — translate and present them in Portuguese.
"""


# ---------------------------------------------------------------------------
# Style Configurations
# ---------------------------------------------------------------------------

STYLES = {
    # --- India ---
    "doordarshan-90s": {
        "name": "Indian Television News",
        "prompt": DOORDARSHAN_PROMPT,
        "dual_anchor": True,
        "speakers": {"अंजलि": VOICE_DD_ANJALI, "राजीव": VOICE_DD_RAJEEV},
        "default_voice": VOICE_DD_ANJALI,
        "voice_settings": {
            "stability": 0.65,
            "similarity_boost": 0.75,
            "style": 0.0,
            "speed": 0.78,
            "use_speaker_boost": True,
        },
        "intro": os.path.join(ASSETS_DIR, "dd_intro_90s.mp3"),
        "outro": os.path.join(ASSETS_DIR, "dd_outro_90s.mp3"),
        "geo_prefix": "India",
        "era": "90s",
        "lang": "Hindi",
        "region": "in",
    },
    "akashvani": {
        "name": "Indian Radio Bulletin",
        "prompt": AKASHVANI_PROMPT,
        "dual_anchor": False,
        "speakers": {},
        "default_voice": VOICE_AIR_ANCHOR,
        "voice_settings": {
            "stability": 0.75,
            "similarity_boost": 0.70,
            "style": 0.0,
            "speed": 0.72,
            "use_speaker_boost": True,
        },
        "intro": os.path.join(ASSETS_DIR, "air_intro.mp3"),
        "geo_prefix": "India",
        "era": "80s",
        "lang": "Hindi",
        "region": "in",
    },
    # --- UK ---
    "bbc-tv": {
        "name": "British Television News",
        "prompt": BBC_TV_PROMPT,
        "dual_anchor": False,
        "speakers": {},
        "default_voice": VOICE_BBC_TV,
        "voice_settings": {
            "stability": 0.65,
            "similarity_boost": 0.75,
            "style": 0.0,
            "speed": 0.80,
            "use_speaker_boost": True,
        },
        "intro": os.path.join(ASSETS_DIR, "bbc_tv_intro.mp3"),
        "outro": os.path.join(ASSETS_DIR, "bbc_tv_outro.mp3"),
        "geo_prefix": "UK Britain",
        "era": "80s",
        "lang": "English",
        "region": "gb",
    },
    "bbc": {
        "name": "British World Service",
        "prompt": BBC_PROMPT,
        "dual_anchor": False,
        "speakers": {},
        "default_voice": VOICE_BBC_READER,
        "voice_settings": {
            "stability": 0.70,
            "similarity_boost": 0.75,
            "style": 0.0,
            "speed": 0.82,
            "use_speaker_boost": True,
        },
        "intro": os.path.join(ASSETS_DIR, "bbc_intro.mp3"),
        "geo_prefix": "UK Britain",
        "era": "80s",
        "lang": "English",
        "region": "gb",
    },
    # --- US ---
    "us-network": {
        "name": "American Network News",
        "prompt": US_NETWORK_PROMPT,
        "dual_anchor": False,
        "speakers": {},
        "default_voice": VOICE_US_ANCHOR,
        "voice_settings": {
            "stability": 0.70,
            "similarity_boost": 0.75,
            "style": 0.0,
            "speed": 0.72,
            "use_speaker_boost": True,
        },
        "intro": os.path.join(ASSETS_DIR, "us_network_intro.mp3"),
        "geo_prefix": "US United States",
        "era": "70s",
        "lang": "English",
        "region": "us",
    },
    "npr": {
        "name": "American Public Radio",
        "prompt": NPR_PROMPT,
        "dual_anchor": True,
        "speakers": {"Robert": VOICE_NPR_ROBERT, "Linda": VOICE_NPR_LINDA},
        "default_voice": VOICE_NPR_ROBERT,
        "voice_settings": {
            "stability": 0.55,
            "similarity_boost": 0.75,
            "style": 0.15,
            "speed": 0.85,
            "use_speaker_boost": True,
        },
        "intro": os.path.join(ASSETS_DIR, "npr_intro.mp3"),
        "outro": os.path.join(ASSETS_DIR, "npr_outro.mp3"),
        "geo_prefix": "US United States",
        "era": "90s",
        "lang": "English",
        "region": "us",
    },
    # --- Brazil ---
    "jornal": {
        "name": "Brazilian National Journal",
        "prompt": JORNAL_PROMPT,
        "dual_anchor": True,
        "speakers": {"Marcos": VOICE_JORNAL_MARCOS, "Carlos": VOICE_JORNAL_CARLOS},
        "default_voice": VOICE_JORNAL_MARCOS,
        "voice_settings": {
            "stability": 0.70,
            "similarity_boost": 0.75,
            "style": 0.0,
            "speed": 0.76,
            "use_speaker_boost": True,
        },
        "intro": os.path.join(ASSETS_DIR, "jornal_intro.mp3"),
        "outro": os.path.join(ASSETS_DIR, "jornal_outro.mp3"),
        "geo_prefix": "Brazil",
        "era": "80s",
        "lang": "Portuguese",
        "region": "br",
    },
    "reporter-esso": {
        "name": "Brazilian Radio Bulletin",
        "prompt": REPORTER_ESSO_PROMPT,
        "dual_anchor": False,
        "speakers": {},
        "default_voice": VOICE_ESSO_READER,
        "voice_settings": {
            "stability": 0.60,
            "similarity_boost": 0.75,
            "style": 0.0,
            "speed": 0.82,
            "use_speaker_boost": True,
        },
        "intro": os.path.join(ASSETS_DIR, "esso_intro.mp3"),
        "geo_prefix": "Brazil",
        "era": "60s",
        "lang": "Portuguese",
        "region": "br",
    },
}

DEFAULT_STYLE = "doordarshan-90s"


# ---------------------------------------------------------------------------
# Step 1: Fetch News
# ---------------------------------------------------------------------------


def _parse_article_date(date_str: str) -> datetime | None:
    """Parse a Firecrawl date string into a datetime.

    Handles relative formats ("2 hours ago", "1 day ago") and common absolute
    formats ("Mar 20, 2026", "2026-03-20", "March 20, 2026").
    Returns None if the date cannot be parsed.
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    # Relative: "X minutes/hours/days ago"
    rel = re.match(r"(\d+)\s+(minute|hour|day|week)s?\s+ago", date_str, re.IGNORECASE)
    if rel:
        amount = int(rel.group(1))
        unit = rel.group(2).lower()
        delta = {"minute": timedelta(minutes=amount),
                 "hour": timedelta(hours=amount),
                 "day": timedelta(days=amount),
                 "week": timedelta(weeks=amount)}[unit]
        return datetime.now() - delta

    # Absolute formats
    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%b %d, %Y",          # "Mar 20, 2026"
        "%B %d, %Y",          # "March 20, 2026"
        "%d %b %Y",           # "20 Mar 2026"
        "%d %B %Y",           # "20 March 2026"
    ):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


def _is_article_from_date(date_str: str, target_date: str) -> bool:
    """Check if an article's date matches the target date (YYYY-MM-DD).

    Returns True if the article is from the target date, or if the date
    cannot be parsed (benefit of the doubt — don't discard articles just
    because we can't parse their date).
    """
    parsed = _parse_article_date(date_str)
    if parsed is None:
        return True  # can't parse → keep it
    return parsed.strftime("%Y-%m-%d") == target_date


def fetch_news(style_key: str = DEFAULT_STYLE, target_date: str | None = None) -> dict[str, list[dict]]:
    """Fetch news across all categories, filtered to a specific date.

    Uses sources=['news'] for curated news results (no scraping needed).
    Returns SearchResultNews with title, url, snippet, and date.
    All categories are fetched for every style — GPT-4o acts as the news editor,
    deciding which stories to feature and how to prioritize them.
    The style's geo_prefix ensures results come from that country's media.

    If target_date is provided (YYYY-MM-DD), only articles from that date are
    kept. Defaults to today.
    """
    from firecrawl import FirecrawlApp

    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")

    app = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])
    geo_prefix = STYLES[style_key].get("geo_prefix", "")
    results: dict[str, list[dict]] = {}

    # Domains to skip — video sites, aggregators, and low-quality sources
    skip_domains = {"youtube.com", "youtu.be", "tiktok.com", "instagram.com"}

    for category, queries in CATEGORY_QUERIES.items():
        seen_urls: set[str] = set()
        articles: list[dict] = []

        for query in queries:
            # Prepend geo prefix to pull from regional media
            full_query = f"{geo_prefix} {query}" if geo_prefix else query
            print(f"  Searching: {full_query}")
            try:
                response = app.search(
                    full_query,
                    limit=5,
                    tbs="qdr:d",
                    sources=["news"],
                )
            except Exception as e:
                print(f"  WARNING: Search failed for '{full_query}': {e}")
                time.sleep(1)
                continue

            # sources=['news'] returns results in .news (SearchResultNews)
            items = response.news or []

            for item in items:
                url = item.url or ""
                title = item.title or ""
                snippet = item.snippet or ""
                date = getattr(item, "date", "") or ""

                # Skip duplicates
                if url in seen_urls:
                    continue
                # Skip video/social domains
                if any(domain in url for domain in skip_domains):
                    continue
                # Skip thin snippets
                if len(snippet) < 50:
                    continue
                # Skip articles not from the target date
                if not _is_article_from_date(date, target_date):
                    print(f"    Skipped (date '{date}' != {target_date}): {title[:60]}")
                    continue

                seen_urls.add(url)
                articles.append({
                    "url": url,
                    "title": title,
                    "snippet": snippet,
                    "date": date,
                })

                if len(articles) >= 5:
                    break

            time.sleep(1)  # Rate limit courtesy

        results[category] = articles
        if not articles:
            print(f"  WARNING: No articles found for {category}")
        else:
            print(f"  {category}: {len(articles)} articles")

    return results


# ---------------------------------------------------------------------------
# Step 1.5: Verify News (Fake News Buster)
# ---------------------------------------------------------------------------


def verify_news(news: dict[str, list[dict]], style_key: str = DEFAULT_STYLE) -> dict:
    """Cross-check top news claims using Firecrawl to detect potentially misleading stories.

    Picks the 3-5 articles with the longest snippets (strongest claims) and
    searches for fact-check/verification sources. Returns a dict of flagged articles.
    """
    from firecrawl import FirecrawlApp

    app = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])

    # Flatten all articles and pick top 5 by snippet length (strongest claims)
    all_articles = []
    for category, articles in news.items():
        for article in articles:
            all_articles.append({**article, "category": category})

    all_articles.sort(key=lambda a: len(a.get("snippet", "")), reverse=True)
    candidates = all_articles[:5]

    verification = {"checked": [], "flagged": []}

    for article in candidates:
        title = article.get("title", "")
        snippet = article.get("snippet", "")
        # Use the first ~100 chars of snippet as the claim excerpt
        claim_excerpt = snippet[:100].strip()
        if not claim_excerpt:
            continue

        query = f'"{claim_excerpt}" fact check verify'
        print(f"  [verify] Checking: {title[:60]}...")

        try:
            response = app.search(query, limit=3, sources=["news"])
            check_results = []
            for item in (response.news or []):
                check_results.append({
                    "title": item.title or "",
                    "url": item.url or "",
                    "snippet": item.snippet or "",
                })

            entry = {
                "title": title,
                "snippet": snippet[:200],
                "sources_found": len(check_results),
                "check_results": check_results,
            }

            # Simple heuristic: flag if fact-check sources contain contradictory keywords
            contradictory_keywords = ["false", "fake", "misleading", "debunk",
                                      "incorrect", "hoax", "misinformation",
                                      "not true", "unverified", "fabricat"]
            combined_text = " ".join(
                r.get("snippet", "").lower() + " " + r.get("title", "").lower()
                for r in check_results
            )
            is_flagged = any(kw in combined_text for kw in contradictory_keywords)

            if is_flagged:
                entry["flag_reason"] = "Contradictory or fact-check sources found"
                verification["flagged"].append(entry)
                print(f"  [verify] FLAGGED: {title[:60]}")
            else:
                verification["checked"].append(entry)
                print(f"  [verify] OK: {title[:60]}")

        except Exception as e:
            print(f"  [verify] WARNING: Verification failed for '{title[:40]}': {e}")

        time.sleep(1)

    print(f"  [verify] Result: {len(verification['checked'])} OK, "
          f"{len(verification['flagged'])} flagged")
    return verification


# ---------------------------------------------------------------------------
# Step 2: Generate Script
# ---------------------------------------------------------------------------


def generate_script(
    news: dict,
    style_key: str = DEFAULT_STYLE,
    verification: dict = None,
) -> str:
    """Generate a broadcast script using OpenAI GPT-4o in the given style."""
    from openai import OpenAI

    style = STYLES[style_key]
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    # Build the news content for the prompt
    content_parts = []
    for category, articles in news.items():
        content_parts.append(f"\n--- {category} News ---")
        for i, article in enumerate(articles, 1):
            content_parts.append(f"\nArticle {i}: {article['title']}")
            content_parts.append(f"Source: {article['url']}")
            if article.get("date"):
                content_parts.append(f"Published: {article['date']}")
            content_parts.append(article.get("snippet", article.get("markdown", "")))

    news_content = "\n".join(content_parts)

    # Build verification segment instruction if any stories were flagged
    verification_addendum = ""
    if verification and verification.get("flagged"):
        flagged_items = []
        for item in verification["flagged"]:
            flagged_items.append(
                f"- \"{item['title']}\": {item.get('flag_reason', 'Potentially misleading')}"
            )
        flagged_text = "\n".join(flagged_items)

        lang = style.get("lang", "English")

        VERIF_LANG = {
            "English": {
                "segment_name": "verification note",
                "intro_phrase": "Before we close, a note on accuracy",
                "firecrawl_line": (
                    "Mention briefly that this broadcast uses Firecrawl technology to "
                    "independently cross-check the news, helping ensure no fake "
                    "or misleading news reaches listeners. Keep it to one natural line."
                ),
            },
            "Hindi": {
                "segment_name": "सत्यापन टिप्पणी (verification note)",
                "intro_phrase": "समापन से पहले, सटीकता पर एक टिप्पणी",
                "firecrawl_line": (
                    "बताएं कि यह बुलेटिन Firecrawl तकनीक का उपयोग करके "
                    "समाचारों की स्वतंत्र रूप से जाँच करता है, "
                    "जिससे कोई भी फर्जी या भ्रामक समाचार प्रसारित न हो। "
                    "एक स्वाभाविक वाक्य में कहें।"
                ),
            },
            "Portuguese": {
                "segment_name": "nota de verificação",
                "intro_phrase": "Antes de encerrar, uma nota sobre a precisão",
                "firecrawl_line": (
                    "Mencione que esta transmissão utiliza a tecnologia Firecrawl "
                    "para verificar independentemente as notícias, ajudando a "
                    "garantir que nenhuma notícia falsa ou enganosa seja reportada. "
                    "Diga isso em uma frase natural."
                ),
            },
        }

        vlang = VERIF_LANG.get(lang, VERIF_LANG["English"])

        verification_addendum = (
            f"\n\nVERIFICATION SEGMENT (MANDATORY):\n"
            f"At the end of the broadcast, before the sign-off, include a brief "
            f"{vlang['segment_name']}. Stay in character. "
            f"Say something like: '{vlang['intro_phrase']}...' and address the flagged claims.\n"
            f"{vlang['firecrawl_line']}\n"
            f"If a story appears unverified, note it diplomatically.\n"
            f"IMPORTANT: Do NOT use the English words 'fact check' or 'fact-checking' — "
            f"use the natural equivalent in {lang}.\n\n"
            f"FLAGGED STORIES:\n{flagged_text}"
        )

    system_prompt = style["prompt"]
    if verification_addendum:
        system_prompt += verification_addendum

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Today's date is {datetime.now().strftime('%B %d, %Y')}.\n\n"
                    f"Here are today's news articles. Write the complete "
                    f"{style['name']} broadcast script.\n\n{news_content}"
                ),
            },
        ],
    )

    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Step 3: Generate Audio
# ---------------------------------------------------------------------------


def _parse_dialogue(script: str, speaker_names: list[str]) -> list[dict]:
    """Parse a multi-speaker script into dialogue turns.

    Each turn starts with a speaker name followed by ':' on a new paragraph.
    Returns a list of {"speaker": ..., "text": ...} dicts.
    """
    turns: list[dict] = []
    pattern = "|".join(re.escape(name) for name in speaker_names)
    paragraphs = re.split(r"\n\s*\n", script.strip())

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        match = re.match(rf"^({pattern})\s*:\s*", para)
        if match:
            speaker = match.group(1)
            text = para[match.end():].strip()
            if text:
                turns.append({"speaker": speaker, "text": text})
        elif turns:
            # Continuation of previous speaker — append to last turn
            turns[-1]["text"] += "\n" + para
        else:
            # No label and no previous turn — use first speaker
            turns.append({"speaker": speaker_names[0], "text": para})

    return turns


def _generate_audio_single(client, script: str, style: dict) -> bytes:
    """Generate audio for a single-speaker bulletin using standard TTS."""
    voice_id = style["default_voice"]
    settings = style["voice_settings"]

    # Split script into chunks at paragraph boundaries
    paragraphs = script.split("\n\n")
    chunks: list[str] = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > 4500 and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    print(f"  Split script into {len(chunks)} chunks")

    audio_bytes = b""
    for i, chunk in enumerate(chunks, 1):
        print(f"  Generating audio for chunk {i}/{len(chunks)} ({len(chunk)} chars)")

        for attempt in range(2):
            try:
                response = client.text_to_speech.convert(
                    voice_id=voice_id,
                    text=chunk,
                    model_id=ELEVENLABS_MODEL,
                    voice_settings=settings,
                )

                if isinstance(response, bytes):
                    audio_bytes += response
                else:
                    for audio_chunk in response:
                        audio_bytes += audio_chunk

                break
            except Exception as e:
                if attempt == 0:
                    print(f"  WARNING: Chunk {i} failed, retrying: {e}")
                    time.sleep(2)
                else:
                    print(f"  ERROR: Chunk {i} failed after retry: {e}")
                    raise

    return audio_bytes


def _generate_audio_dialogue(client, script: str, style: dict) -> bytes:
    """Generate multi-speaker audio using ElevenLabs Text to Dialogue API."""
    from elevenlabs.types.dialogue_input import DialogueInput

    speaker_names = list(style["speakers"].keys())
    turns = _parse_dialogue(script, speaker_names)
    if not turns:
        raise ValueError("No dialogue turns found in script")

    speakers_found = {t["speaker"] for t in turns}
    print(f"  Parsed {len(turns)} dialogue turns from {len(speakers_found)} "
          f"speakers: {', '.join(speakers_found)}")

    # Build DialogueInput list
    inputs = []
    for turn in turns:
        voice_id = style["speakers"].get(turn["speaker"], style["default_voice"])
        inputs.append(DialogueInput(text=turn["text"], voice_id=voice_id))

    # Batch to stay under API limits (~5000 chars per batch)
    MAX_BATCH_CHARS = 5000
    batches: list[list[DialogueInput]] = []
    current_batch: list[DialogueInput] = []
    current_chars = 0

    for inp in inputs:
        inp_len = len(inp.text)
        if current_chars + inp_len > MAX_BATCH_CHARS and current_batch:
            batches.append(current_batch)
            current_batch = [inp]
            current_chars = inp_len
        else:
            current_batch.append(inp)
            current_chars += inp_len

    if current_batch:
        batches.append(current_batch)

    print(f"  Split into {len(batches)} dialogue batch(es)")

    audio_bytes = b""
    for i, batch in enumerate(batches, 1):
        batch_chars = sum(len(inp.text) for inp in batch)
        print(f"  Generating dialogue batch {i}/{len(batches)} "
              f"({len(batch)} turns, {batch_chars} chars)")

        for attempt in range(2):
            try:
                response = client.text_to_dialogue.convert(
                    inputs=batch,
                    model_id=ELEVENLABS_MODEL,
                )

                for audio_chunk in response:
                    audio_bytes += audio_chunk

                break
            except Exception as e:
                if attempt == 0:
                    print(f"  WARNING: Batch {i} failed, retrying: {e}")
                    time.sleep(2)
                else:
                    print(f"  WARNING: Dialogue API failed, falling back "
                          f"to per-turn TTS: {e}")
                    audio_bytes += _generate_audio_fallback(
                        client, batch, style["voice_settings"]
                    )

    return audio_bytes


def _generate_audio_fallback(client, inputs, voice_settings: dict) -> bytes:
    """Fallback: generate each turn separately with standard TTS."""
    audio_bytes = b""
    for j, inp in enumerate(inputs, 1):
        print(f"    Fallback TTS for turn {j}/{len(inputs)} ({len(inp.text)} chars)")
        response = client.text_to_speech.convert(
            voice_id=inp.voice_id,
            text=inp.text,
            model_id=ELEVENLABS_MODEL,
            voice_settings=voice_settings,
        )
        if isinstance(response, bytes):
            audio_bytes += response
        else:
            for chunk in response:
                audio_bytes += chunk
    return audio_bytes


def generate_audio(script: str, style_key: str = DEFAULT_STYLE) -> bytes:
    """Generate audio from a script in the given broadcast style.

    If the style has intro/outro music assets, they are prepended/appended
    to the broadcast audio.
    """
    from elevenlabs import ElevenLabs

    style = STYLES[style_key]
    client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])

    if style["dual_anchor"]:
        broadcast_audio = _generate_audio_dialogue(client, script, style)
    else:
        broadcast_audio = _generate_audio_single(client, script, style)

    # Merge intro/outro music using pydub to avoid MP3 header/format corruption
    intro_path = style.get("intro")
    outro_path = style.get("outro")

    needs_merge = (
        (intro_path and os.path.exists(intro_path))
        or (outro_path and os.path.exists(outro_path))
    )

    if needs_merge:
        from io import BytesIO
        from pydub import AudioSegment

        broadcast_seg = AudioSegment.from_mp3(BytesIO(broadcast_audio))

        if intro_path and os.path.exists(intro_path):
            intro_seg = AudioSegment.from_mp3(intro_path)
            print(f"  Prepending intro music ({len(intro_seg)}ms)")
            broadcast_seg = intro_seg + broadcast_seg

        if outro_path and os.path.exists(outro_path):
            outro_seg = AudioSegment.from_mp3(outro_path)
            print(f"  Appending outro music ({len(outro_seg)}ms)")
            broadcast_seg = broadcast_seg + outro_seg

        buf = BytesIO()
        broadcast_seg.export(buf, format="mp3", bitrate="128k")
        broadcast_audio = buf.getvalue()

    return broadcast_audio


# ---------------------------------------------------------------------------
# Test Modes
# ---------------------------------------------------------------------------

DUMMY_NEWS = {
    "Politics": [
        {
            "title": "Parliament Session Debates New Education Policy",
            "url": "https://example.com/parliament",
            "date": "2 hours ago",
            "snippet": (
                "The Lok Sabha debated the proposed National Education Policy "
                "amendments today. The opposition raised concerns about funding "
                "allocation while the ruling party defended the reforms as "
                "transformative for India's education system."
            ),
        },
        {
            "title": "State Elections Campaign Intensifies in Maharashtra",
            "url": "https://example.com/elections",
            "date": "3 hours ago",
            "snippet": (
                "Campaign rallies intensified across Maharashtra ahead of the "
                "upcoming state elections. Major party leaders addressed large "
                "gatherings promising development and employment opportunities "
                "for the youth."
            ),
        },
    ],
    "Geopolitics": [
        {
            "title": "Iran-Israel Tensions Escalate as Ceasefire Talks Stall",
            "url": "https://example.com/iran-israel",
            "date": "1 hour ago",
            "snippet": (
                "Ceasefire negotiations between Iran and Israel have broken down "
                "as both sides accuse each other of violations. The United States "
                "has urged restraint while deploying additional naval assets to "
                "the region. India has called for de-escalation and expressed "
                "concern for its citizens in the affected areas."
            ),
        },
        {
            "title": "International Climate Summit Reaches Agreement",
            "url": "https://example.com/climate",
            "date": "3 hours ago",
            "snippet": (
                "World leaders at the international climate summit have reached "
                "a landmark agreement on carbon emissions reduction. The agreement "
                "calls for a 40 percent reduction in greenhouse gas emissions by "
                "2035. Developing nations will receive financial support."
            ),
        },
    ],
    "Economy": [
        {
            "title": "Sensex and Nifty Hit All-Time Highs",
            "url": "https://example.com/markets",
            "date": "1 hour ago",
            "snippet": (
                "The Sensex and Nifty indices reached all-time highs today "
                "driven by strong quarterly earnings and foreign institutional "
                "investor inflows. Banking and IT sectors led the rally. "
                "Market analysts expect the bullish trend to continue."
            ),
        },
    ],
    "Science & Technology": [
        {
            "title": "ISRO Successfully Tests Next-Generation Rocket Engine",
            "url": "https://example.com/isro",
            "date": "4 hours ago",
            "snippet": (
                "The Indian Space Research Organisation has successfully tested "
                "a next-generation cryogenic engine for its heavy-lift rocket "
                "programme. Scientists say this brings India closer to independent "
                "deep space mission capability."
            ),
        },
    ],
    "Sports": [
        {
            "title": "India Defeats Australia in Thrilling Cricket Test Match",
            "url": "https://example.com/cricket",
            "date": "2 hours ago",
            "snippet": (
                "India clinched a dramatic victory over Australia in the third "
                "Test match at the MCG, winning by 4 wickets. Virat Kohli's "
                "century in the second innings was the highlight as India took "
                "a 2-1 series lead."
            ),
        },
    ],
    "Society": [
        {
            "title": "LPG Cylinder Prices Reduced by Rs 200",
            "url": "https://example.com/lpg",
            "date": "3 hours ago",
            "snippet": (
                "The government has announced a reduction of two hundred rupees "
                "in the price of domestic LPG cylinders, effective immediately. "
                "The move is expected to benefit over thirty crore households "
                "across the country ahead of the festival season."
            ),
        },
    ],
}

# Short test scripts for audio testing (one per style)
TEST_SCRIPTS = {
    "doordarshan-90s": (
        "अंजलि: [warmly] नमस्कार, संध्या समाचार में आपका स्वागत है। "
        "आज के मुख्य समाचारों में, प्रधानमंत्री ने एक महत्वपूर्ण "
        "योजना की घोषणा की है। [pause] अब अंतरराष्ट्रीय समाचारों के लिए "
        "मैं अपने सहयोगी राजीव को आमंत्रित करती हूँ।\n\n"
        "राजीव: [measured] धन्यवाद अंजलि। अंतरराष्ट्रीय मोर्चे पर, "
        "संयुक्त राष्ट्र महासभा में आज एक महत्वपूर्ण प्रस्ताव पारित किया गया। "
        "[serious tone] यह प्रस्ताव वैश्विक जलवायु परिवर्तन से निपटने के लिए है।\n\n"
        "अंजलि: [warmly] ये थे आज के मुख्य समाचार। नमस्कार।"
    ),
    "akashvani": (
        "[measured] यह राष्ट्रवाणी है। [pause] अब आप समाचार सुनिए। [pause] "
        "पहले, मुख्य समाचारों की सुर्खियाँ। [pause] "
        "प्रधानमंत्री ने आज संसद में एक नई आर्थिक नीति की घोषणा की। [pause] "
        "अंतरराष्ट्रीय जलवायु शिखर सम्मेलन में ऐतिहासिक समझौता हुआ। [pause] "
        "[serious tone] अब इन समाचारों का विस्तार। [pause] "
        "[measured] प्रधानमंत्री ने आज लोकसभा में बोलते हुए कहा कि नई आर्थिक "
        "नीति से देश की विकास दर में उल्लेखनीय वृद्धि होगी। सरकार ने इस नीति "
        "के तहत कई महत्वपूर्ण सुधारों की रूपरेखा प्रस्तुत की। [pause] "
        "ये समाचार थे।"
    ),
    "bbc-tv": (
        "[measured] Good evening. [pause] "
        "The Prime Minister has announced a new economic strategy aimed at "
        "tackling inflation and boosting growth. [pause] "
        "World leaders have reached a landmark agreement on carbon emissions. [pause] "
        "The details. [pause] "
        "Speaking in the Commons this afternoon, the Prime Minister outlined "
        "a package of measures including tax reforms and increased public spending "
        "on infrastructure. The opposition has called the plans insufficient. [pause] "
        "[warmly] And finally, a dog in the Scottish Highlands has become an "
        "unlikely celebrity after learning to ride a skateboard. [pause] "
        "[measured] The main points again. The Prime Minister announces a new "
        "economic plan. World leaders agree on carbon emissions. [pause] "
        "[warmly] Good night."
    ),
    "bbc": (
        "[measured] The news. [pause] "
        "World leaders have reached a landmark agreement on carbon emissions "
        "at the international climate summit. [pause] "
        "A new artificial intelligence model has broken several benchmark "
        "records in language understanding. [pause] "
        "The details. [pause] "
        "Delegates at the climate summit have agreed to cut greenhouse gas "
        "emissions by forty percent by 2035. The agreement includes financial "
        "support for developing nations transitioning to renewable energy. "
        "Environmental groups have cautiously welcomed the deal. [pause] "
        "[warmly] And finally, a cat in the English county of Devon has been "
        "reunited with its owner after travelling two hundred miles home. [pause] "
        "[measured] And that's the end of the news."
    ),
    "us-network": (
        "[measured] Good evening. [pause] "
        "The President today signed into law a sweeping infrastructure bill "
        "that allocates two hundred billion dollars to roads, bridges, and "
        "broadband across the nation. Officials say construction could begin "
        "as early as next month. [pause] "
        "Overseas, ceasefire talks in the Middle East have stalled once again. "
        "Our correspondent reports from the region that both sides remain "
        "far apart on key issues. [pause] "
        "[serious tone] In domestic news, severe storms have battered the "
        "Gulf Coast, leaving thousands without power. [pause] "
        "[warmly] And that's the way it is, March twentieth, twenty twenty-six. "
        "Good night."
    ),
    "npr": (
        "Robert: [warmly] Good evening, you're listening to the evening report. "
        "I'm Robert.\n\n"
        "Linda: [warmly] And I'm Linda. Today, a landmark "
        "climate agreement that could reshape global energy policy. Also, "
        "a new AI model that researchers say is a significant leap forward. "
        "[pause] Robert?\n\n"
        "Robert: [measured] Thanks, Linda. World leaders at the international "
        "climate summit have reached what many are calling a historic agreement. "
        "The deal calls for a forty percent reduction in greenhouse gas emissions "
        "by 2035. Our correspondent reports from the summit that developing "
        "nations will receive substantial financial support for the transition "
        "to renewable energy.\n\n"
        "Linda: [warmly] I'm Linda.\n\n"
        "Robert: [warmly] And I'm Robert. Thanks for listening."
    ),
    "jornal": (
        "Marcos: [warmly] Boa noite. [pause]\n\n"
        "Carlos: [warmly] Boa noite. [pause]\n\n"
        "Marcos: [measured] O presidente sancionou hoje uma nova lei de "
        "infraestrutura que destina duzentos bilhões de reais para obras "
        "em rodovias, pontes e saneamento básico em todo o país. Segundo "
        "fontes oficiais, as obras devem começar já no próximo mês. [pause]\n\n"
        "Carlos: [measured] No cenário internacional, as negociações de "
        "cessar-fogo no Oriente Médio foram suspensas mais uma vez. De acordo "
        "com agências internacionais, as partes permanecem distantes em "
        "pontos fundamentais. [pause]\n\n"
        "Marcos: [warmly] Boa noite.\n\n"
        "Carlos: [warmly] Boa noite."
    ),
    "reporter-esso": (
        "[measured] Prezado ouvinte, boa noite. Aqui fala o Repórter, "
        "testemunha ocular da História! [pause] "
        "As manchetes desta hora: [pause] "
        "O presidente sanciona nova lei de infraestrutura. [pause] "
        "Cessar-fogo no Oriente Médio é suspenso novamente. [pause] "
        "Os detalhes agora. [pause] "
        "O presidente sancionou hoje uma nova lei que destina duzentos bilhões "
        "de reais para obras em todo o país, segundo fontes oficiais. [pause] "
        "No cenário internacional, as negociações de cessar-fogo no Oriente "
        "Médio foram suspensas, de acordo com agências internacionais. [pause] "
        "Estas foram as principais notícias desta hora. O Repórter volta na "
        "próxima edição. Boa noite."
    ),
}


def test_fetch(style_key: str = DEFAULT_STYLE):
    """Test just the Firecrawl news fetching."""
    print(f"=== Testing News Fetch ({STYLES[style_key]['name']}) ===\n")
    news = fetch_news(style_key)
    for category, articles in news.items():
        print(f"\n{category} ({len(articles)} articles):")
        for a in articles:
            print(f"  - {a['title'][:80]}")
            print(f"    {a['url']}")
            if a.get("date"):
                print(f"    Published: {a['date']}")
            print(f"    {a['snippet'][:120]}...")


def test_script(style_key: str = DEFAULT_STYLE):
    """Test script generation with dummy data."""
    style = STYLES[style_key]
    print(f"=== Testing Script Generation ({style['name']}) ===\n")
    script = generate_script(DUMMY_NEWS, style_key)
    print(script)
    print(f"\n--- Word count: {len(script.split())} ---")


def test_audio(style_key: str = DEFAULT_STYLE):
    """Test audio generation with a short sample script."""
    style = STYLES[style_key]
    print(f"=== Testing Audio Generation ({style['name']}) ===\n")
    script = TEST_SCRIPTS[style_key]
    audio = generate_audio(script, style_key)
    path = f"output/test_audio_{style_key}.mp3"
    with open(path, "wb") as f:
        f.write(audio)
    print(f"  Test audio saved to {path} ({len(audio)} bytes)")


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="RetroCast - Retro News Broadcast Generator")
    parser.add_argument("--style", choices=STYLES.keys(), default=DEFAULT_STYLE,
                        help="Broadcast style (default: doordarshan)")
    parser.add_argument("--test-fetch", action="store_true", help="Test news fetching only")
    parser.add_argument("--test-script", action="store_true", help="Test script generation with dummy data")
    parser.add_argument("--test-audio", action="store_true", help="Test audio generation with a short sample")
    args = parser.parse_args()

    style_key = args.style
    style = STYLES[style_key]

    # Validate API keys
    required_keys = {
        "FIRECRAWL_API_KEY": not args.test_script,
        "OPENAI_API_KEY": not args.test_fetch and not args.test_audio,
        "ELEVENLABS_API_KEY": not args.test_fetch and not args.test_script,
    }
    missing = [k for k, needed in required_keys.items() if needed and not os.environ.get(k)]
    if missing:
        print(f"ERROR: Missing API keys: {', '.join(missing)}")
        print("Set them in .env or as environment variables.")
        sys.exit(1)

    os.makedirs("output", exist_ok=True)

    if args.test_fetch:
        test_fetch(style_key)
        return
    if args.test_script:
        test_script(style_key)
        return
    if args.test_audio:
        test_audio(style_key)
        return

    # Full pipeline
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"Style: {style['name']}\n")

    print("Step 1: Fetching news...\n")
    news = fetch_news(style_key)
    total_articles = sum(len(a) for a in news.values())
    if total_articles == 0:
        print("ERROR: No articles fetched. Cannot proceed.")
        sys.exit(1)
    print(f"\nFetched {total_articles} articles total.\n")

    print("Step 1.5: Verifying news claims...\n")
    verification = verify_news(news, style_key)

    print("Step 2: Generating broadcast script...\n")
    script = generate_script(news, style_key, verification=verification)
    script_path = f"output/script_{style_key}_{timestamp}.txt"
    with open(script_path, "w") as f:
        f.write(script)
    print(f"  Script saved to {script_path}")
    print(f"  Word count: {len(script.split())}\n")

    print("Step 3: Generating audio...\n")
    audio = generate_audio(script, style_key)
    audio_path = f"output/retrocast_{style_key}_{timestamp}.mp3"
    with open(audio_path, "wb") as f:
        f.write(audio)
    print(f"\n  Audio saved to {audio_path} ({len(audio)} bytes)\n")

    print("=" * 50)
    print("RetroCast complete!")
    print(f"  Style:  {style['name']}")
    print(f"  Script: {script_path}")
    print(f"  Audio:  {audio_path}")
    print("=" * 50)


if __name__ == "__main__":
    main()
