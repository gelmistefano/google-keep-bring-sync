# CLAUDE.md

Guidance for Claude Code working in this repository.

## What this is

Single-file Python script that syncs a **Google Keep** shopping list note into
the **Bring!** shopping app. Runs one-shot per invocation (cron / Docker every
minute). No web server, no persistent state, no tests.

## Layout

- `main.py` — everything. Two classes + `main()`:
  - `Bring` — Bring! REST client (`https://api.getbring.com/rest/v2`): login,
    find list by name prefix, load list, load localized catalog, add item.
  - `GoogleKeep` — `gkeepapi` wrapper: login, read unchecked items from a note
    matched by title, delete synced items.
  - `main()` — reads env vars, wires the two together, runs the sync. Called at
    import time (no `if __name__ == '__main__'` guard).
- `Dockerfile` / `docker-compose.yml` / `entrypoint.sh` — container runs the
  script on a cron schedule (every minute).
- `requirements.txt` — pinned deps (`gkeepapi`, `requests`, crypto libs).
- `README.md` — user-facing setup, env vars, catalog matching behavior.

## Sync flow (`main()`)

1. Google Keep login + `load_shopping_list()` — collect **unchecked** items from
   the note whose title equals `GOOGLE_SHOPPING_LIST_NAME`. Bail early if empty.
2. Bring! `login()` → `find_list()` (name **prefix** match) → `load_locale()`.
3. For each item, `bring.add_item()`.
4. `keep.delete_items()` — delete the synced (unchecked) items from Keep.

## Configuration (env vars)

`BRING_EMAIL`, `BRING_PASSWORD`, `BRING_LIST_NAME` (prefix), `BRING_LOCALE`
(default `it-IT`), `GOOGLE_EMAIL`, `GOOGLE_APP_PASSWORD`,
`GOOGLE_SHOPPING_LIST_NAME`, `GOOGLE_SHOPPING_LIST_SUFFIX_REMOVED` (optional),
`DEBUG` (`TRUE` for verbose logs).

## Catalog matching (the important part)

Goal: reuse Bring!'s **built-in catalog** items (icon + auto section) instead of
creating custom entries.

- Catalog `catalog.<locale>.json`: `itemId` = language-independent key
  (German-based, e.g. `Milch`), `name` = localized display (e.g. `Latte`).
- **Send the `itemId` as `purchase`** → Bring! recognizes the built-in item.
  Sending free text creates a custom item.
- `load_locale()` builds `dictionary[normalize(name)] -> itemId`.
- `match_item()` does exact normalized match, else longest contiguous word-run;
  leftover words go to the Bring! `specification` field. No match → custom item.
- `normalize()` strips accents, lowercases, collapses whitespace. **Match on
  normalized text on both sides** — do not compare raw/`.title()`d strings
  against the dict (that was the original bug: title-cased lookup vs lowercase
  keys never hit).

## Conventions

- **2-space indentation** (not PEP8 4). Match it.
- Docstrings on every method (Args/Returns/Raises).
- Log at every step; guard debug-only detail behind `DEBUG == "TRUE"`.
- Never log full request bodies except via `debug_curl_output` under DEBUG
  (contains credentials/tokens).

## Running / testing

- No test suite. Validate matching logic standalone (importing `main` triggers
  `main()` and needs `gkeepapi`) — copy `normalize`/`match_item` into a scratch
  script and test against the live catalog:
  `curl -s https://web.getbring.com/locale/catalog.it-IT.json`.
- Syntax check: `python3 -m py_compile main.py`.
- Full run needs real Bring! + Google credentials; not runnable offline.

## Gotchas

- `main()` runs on import — you cannot `import main` in a test without it
  executing the sync.
- Bring! `X-BRING-API-KEY` header is hardcoded (public webApp key).
- Google needs an **app password**, not the account password.
- `find_list` matches by prefix; `load_shopping_list` matches note title
  **exactly**.
