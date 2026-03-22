# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in RetroCast, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, please email the maintainer directly or use [GitHub's private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability).

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

You should receive a response within 72 hours.

## Scope

The following are in scope:
- Path traversal or injection in server endpoints
- Authentication bypass on webhook or agent endpoints
- SSRF via article fetching
- Exposure of API keys or secrets
- Cross-site scripting (XSS) in the web frontend

The following are out of scope:
- Vulnerabilities in third-party services (Firecrawl, OpenAI, ElevenLabs)
- Rate limiting or denial of service on local/development deployments
- Issues requiring physical access to the server

## API Keys

RetroCast requires API keys for Firecrawl, OpenAI, and ElevenLabs. These are stored in a `.env` file which is gitignored. Never commit API keys to version control. If you believe keys have been exposed, rotate them immediately through each provider's dashboard.
