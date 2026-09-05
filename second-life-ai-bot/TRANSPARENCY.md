# Transparency / No-Surprises Contract

This project is intentionally small enough to audit by eye.

## Outbound network traffic

The bot is designed to contact only:

1. **Second Life / Linden Lab services**, through LibreMetaverse, for avatar login and normal in-world networking.
2. **The AI endpoint you explicitly select** in `.env`:
   - `OLLAMA`: only `OLLAMA_URL`.
   - `SOJI`: only `SOJI_BASE_URL`.
   - `AUTO`: the providers listed in `AUTO_ORDER`, in that exact order.

`OLLAMA` and `SOJI` modes never silently fail over. Only `AUTO` permits fallback.

## Things this project does NOT contain

- No analytics or telemetry.
- No advertising or tracking SDK.
- No automatic updater.
- No remote command-and-control server.
- No hidden moderation provider.
- No browser scraping.
- No credential upload logic.
- No webhook, Discord, Google, OpenAI, or cloud dependency unless you explicitly point an AI URL at one yourself.
- No background persistence/service installation.

## Credentials

`.env` is ignored by git. `.env.example` contains placeholders only. Do not commit your real Second Life password or Soji key.

## AI action allowlist

The model can request only these avatar actions:

`none`, `sit`, `stand`, `dance`, `fly`, `walk`, `jump`

Any other action string is rejected and printed to the console as `ACTION BLOCKED`.
