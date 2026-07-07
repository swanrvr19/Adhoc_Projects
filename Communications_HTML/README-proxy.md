# Local Anthropic API proxy

The trainer page (`speaking-skills-trainer.html`) calls the Anthropic API to
generate custom prompts and news-based scripts. Browsers can't call the API
directly (no auth, CORS-blocked, and embedding a key in HTML would expose it),
so a tiny local proxy holds the key and forwards requests.

## One-time setup

Get an API key from https://console.anthropic.com → **API keys**.

macOS ships with Python 3 built in (`python3 --version` should print
something). No extra installs needed — the proxy uses only the standard
library.

## Run it

From this folder, in a terminal:

```bash
ANTHROPIC_API_KEY=sk-ant-... python3 proxy.py
```

You should see:

```
Proxy listening at http://127.0.0.1:8787
Forwarding POST /v1/messages → api.anthropic.com
```

Leave that terminal running. Open `speaking-skills-trainer.html` in Chrome —
the **Generate Custom Prompt** and **News-Based Script** buttons will now
work. Ctrl+C in the terminal stops the proxy.

## Tip: avoid pasting the key every time

Save it once in your shell profile (`~/.zshrc` or `~/.bashrc`):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Then just run `python3 proxy.py`.

## Security notes

- The proxy binds to `127.0.0.1` only — nothing on your network can reach it.
- **Never commit your API key.** If you save it to a `.env` file or similar,
  add that file to `.gitignore` first.
- The proxy is for local development only. If you ever want to share the
  trainer with others, deploy the same forwarding logic as a serverless
  function so each user doesn't need Python + a key.

## Troubleshooting

- **"Couldn't generate" / network error in the page** — make sure the proxy
  terminal is still running and shows no errors.
- **401 Unauthorized in the proxy log** — your API key is wrong or revoked.
- **Connection refused** — proxy isn't running, or something else is using
  port 8787 (set `PORT=9000 python3 proxy.py` and update the two URLs in
  the HTML to match).
