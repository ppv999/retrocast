# Contributing to RetroCast

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/pvernekar/retrocast.git
cd retrocast
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # Add your API keys
python setup.py         # Validate keys and create ElevenLabs agent
python server.py        # http://localhost:5000
```

Requires [ffmpeg](https://ffmpeg.org/) (`brew install ffmpeg` on macOS).

## Making Changes

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Test locally — run `python setup.py --check` to validate the setup
4. Submit a pull request

## What to Work On

**New broadcast styles** — The most impactful contribution. Each country has a TV and Radio format. To add a new country, follow the template in `.claude/commands/add-country.md`. You'll need:
- A system prompt capturing the era's editorial voice and format conventions
- An ElevenLabs voice that matches the region and time period
- Intro/outro music (public domain or original)

**Bug fixes** — If you find a bug, open an issue first to discuss, then submit a PR.

**Frontend improvements** — The UI is a single `web/index.html` file. Mobile experience, accessibility, and animations are all areas where help is welcome.

## Code Style

- Python: follow the existing conventions in the codebase (no strict linter enforced)
- Keep changes focused — one PR per feature or fix
- Don't add dependencies unless necessary

## Reporting Issues

Use [GitHub Issues](https://github.com/pvernekar/retrocast/issues). Include:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your Python version and OS

## Security

If you find a security vulnerability, **do not open a public issue**. See [SECURITY.md](SECURITY.md) for responsible disclosure instructions.
