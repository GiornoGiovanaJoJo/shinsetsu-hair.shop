# AGENTS.md

## Cursor Cloud specific instructions

### Overview

Shinsetsu Hair is a single-service Python FastAPI application (hair buying website). It serves static HTML/CSS/JS via Jinja2 templates and exposes form-handling API endpoints that forward submissions to Telegram.

### Running the dev server

```bash
cd /workspace
python3 main.py
```

The server starts on `http://0.0.0.0:8000`. The Telegram bot polling starts automatically on startup — expect `aiogram` log lines about bot polling; these are normal and do not indicate errors.

### Key endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Homepage (Jinja2 rendered from `index.html` + `content.json`) |
| `/api/calculate` | POST | Hair price calculation + Telegram notification |
| `/api/callback` | POST | Callback request + Telegram notification |
| `/styles.css`, `/script.js` | GET | Static assets |

### Gotchas

- **No database**: all data is in-memory (`PRICE_TABLE` dict) or in `content.json`. No migrations needed.
- **No automated test suite**: the codebase has no `tests/` directory or test framework. Verify changes via `curl` against the running server or manual browser testing.
- **No linter/formatter configured**: no `pyproject.toml`, `setup.cfg`, or `.flake8` present. You can run `python3 -m py_compile main.py` for basic syntax validation.
- **Telegram bot token is hardcoded** in `main.py`. The bot will attempt polling on startup. If the token is invalid or rate-limited, errors appear in logs but the web UI still functions normally.
- **Static files are mounted from the repo root** (`StaticFiles(directory=".")`), so the working directory must be `/workspace` when starting the server.
