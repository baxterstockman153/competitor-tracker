---
description: Scrape competitor job boards, classify postings, and generate a strategic hiring analysis. Add a question after the command to ask about specific competitors or trends instead.
user-invocable: true
---

## Setup

- Project directory: use the current working directory (it should contain `main.py` and `competitors.yaml`).
- Always activate the virtualenv: `.venv/bin/python`
- The CLI entrypoint is `main.py`

## Default behavior (no arguments)

Run the full pipeline in order:

1. **Scrape**: `python main.py scrape`
2. **Classify**: `python main.py classify` (requires ANTHROPIC_API_KEY)
3. **Insights**: `python main.py insights --output markdown`

Display the insights output to the user. Do NOT add your own commentary or interpretation — the insights report IS the output.

If any step fails, show the error and continue to the next step where possible (e.g. if classify fails, still run insights with whatever data exists).

## Conversational mode (user provides arguments)

When the user provides text after the command (e.g. `/competitor-tracker what is Cohere Health focusing on?`), do NOT run the full pipeline. Instead:

1. Check when data was last scraped by running `python main.py stats`. If no data exists, run `python main.py scrape` first.
2. Use the available commands to answer the question:
   - `python main.py jobs --function <fn> --domain <domain> --group-by <field>` for browsing/filtering jobs
   - `python main.py weekly --output markdown` for a summary view
   - `python main.py insights --history 3` to review recent analyses
   - `python main.py stats` for high-level numbers
3. Synthesize the command outputs to answer the user's question directly.
