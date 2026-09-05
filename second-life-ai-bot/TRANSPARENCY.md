# Transparency / No-Surprises Contract

This project is intentionally small enough to audit by eye.

## Outbound network traffic

The bot is designed to contact only:

1. **Second Life / Linden Lab services**, through LibreMetaverse, for avatar login, movement/following, and normal in-world networking.
2. **The AI endpoint you explicitly select** in `.env`:
   - `OLLAMA`: only `OLLAMA_URL`.
   - `SOJI`: only `SOJI_BASE_URL`.
   - `AUTO`: the providers listed in `AUTO_ORDER`, in that exact order.

`OLLAMA` and `SOJI` modes never silently fail over. Only `AUTO` permits fallback.

## Owner follow behavior

- The follow target is exactly `OWNER_UUID` from `.env`.
- Follow starts only when `FOLLOW_OWNER_ON_START=true` or the owner sends `!follow on`.
- Movement uses LibreMetaverse / Second Life simulator autopilot toward the owner's observed global position.
- The bot stops inside `FOLLOW_DISTANCE_METERS`.
- If the owner is no longer visible to the connected simulators, the bot cancels autopilot and waits. It does not guess a destination or contact an extra tracking service.
- Only `OWNER_UUID` can use `!follow`, `!provider`, `!model`, `!ai`, or `!action` commands.

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
- No hidden avatar-tracking service.

## Credentials

`.env` is ignored by git. `.env.example` contains placeholders only. Do not commit your real Second Life password or Soji key.

## AI action allowlist

The model can request only these avatar actions:

`none`, `sit`, `stand`, `dance`, `fly`, `walk`, `jump`

Any other action string is rejected and printed to the console as `ACTION BLOCKED`.
