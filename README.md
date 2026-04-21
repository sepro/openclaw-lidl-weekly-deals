# Lidl Weekly Deals — OpenClaw Skill

An [OpenClaw](https://openclaw.ai) skill that fetches the current weekly promotions from [lidl.be](https://www.lidl.be), filters them for a health-conscious couple, and suggests recipes using the discounted ingredients.

## How it works

1. The agent runs `lidl_promotions.py`, a standard-library-only Python scraper that fetches the weekly offers directly from the Lidl website.
2. The agent reads the JSON output, picks the healthiest items, and proposes 3–5 recipes using those ingredients.

No API keys or external Python packages are required.

## Requirements

- Python 3.8 or later (must be on your `PATH` as `python`)
- OpenClaw installed and configured

## Installation

Copy the skill directory into OpenClaw's skills folder:

**macOS / Linux**
```bash
cp -r lidl_weekly_deals ~/.openclaw/workspace/skills/
```

**Windows (PowerShell)**
```powershell
Copy-Item -Recurse lidl_weekly_deals "$env:USERPROFILE\.openclaw\workspace\skills\"
```

Verify the skill was picked up:
```bash
openclaw skills list
```

You should see `lidl_weekly_deals` in the output.

## Usage

Start an OpenClaw session and ask, for example:

> "What are the healthy deals at Lidl this week?"
> "Fetch the Lidl promotions and suggest some recipes."
> "What can we cook this week from the Lidl offers?"

The agent will run the scraper, filter for nutritious items, and return a shortlist with recipe suggestions.

## Skill structure

```
lidl_weekly_deals/
├── SKILL.md            # OpenClaw skill definition and agent instructions
└── lidl_promotions.py  # Scraper — fetches and parses lidl.be
```

## Updating

Re-copy the directory after pulling updates:

```bash
cp -r lidl_weekly_deals ~/.openclaw/workspace/skills/
```
