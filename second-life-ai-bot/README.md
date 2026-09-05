# Second Life AI Bot

A transparent Second Life bot controlled by either a **local Ollama model** or **Soji**. It uses LibreMetaverse 3.1.4 to log a bot avatar into Second Life, listens for IMs, can follow its owner around, asks the selected AI what to say/do, then executes only a small allowlisted set of avatar actions.

## Provider rules

- `AI_PROVIDER=OLLAMA` — local Ollama only; **no fallback**.
- `AI_PROVIDER=SOJI` — Soji only; **no fallback**.
- `AI_PROVIDER=AUTO` — fallback is allowed, in the exact `AUTO_ORDER` you configure.

Default local model: `qwen3-airoguelite-fast:latest` on `127.0.0.1:11434`.

## Requirements

- Windows 10/11
- .NET 8 SDK or newer
- A separate Second Life account for the bot
- Ollama running locally, Soji credentials/endpoint, or both

Second Life treats automated avatars as **Scripted Agents**. Mark the bot account as a Scripted Agent in the Second Life account controls before using it as a bot.

## Setup

```powershell
cd second-life-ai-bot
.\run.ps1
```

On first run, `run.ps1` copies `.env.example` to `.env` and stops so you can fill it in. Your real `.env` is git-ignored.

At minimum set:

```ini
SL_FIRST_NAME=YourBot
SL_LAST_NAME=Resident
SL_PASSWORD=your-password
OWNER_UUID=your-own-avatar-uuid
AI_PROVIDER=OLLAMA
```

Then run `.\run.ps1` again.

## Owner follow mode

The bot follows the avatar identified by `OWNER_UUID`. Follow mode starts automatically by default:

```ini
FOLLOW_OWNER_ON_START=true
FOLLOW_DISTANCE_METERS=3.0
FOLLOW_UPDATE_MS=750
```

It repeatedly locates your avatar in the simulators the client can currently see and uses Second Life simulator autopilot to move toward your global position. Once it is within `FOLLOW_DISTANCE_METERS`, it cancels autopilot and waits until you move away again.

Normal region-border crossings are handled using global region coordinates. If you teleport far enough away that the bot can no longer see your avatar in any connected simulator, it stops moving and waits to reacquire you rather than guessing where you went.

Owner-only IM controls:

```text
!follow on
!follow off
!follow distance 5
!follow 5
!status
```

The follow distance is clamped between 1.5 and 20 meters. Changes made by IM last for the current run; edit `.env` to make a new distance the startup default.

## What the AI can control

The AI returns a tiny JSON action envelope. The program itself validates the action and allows only:

- `none`
- `sit`
- `stand`
- `dance`
- `fly`
- `walk`
- `jump`

Unsupported actions are blocked rather than executed. Follow mode itself is deterministic code tied to `OWNER_UUID`; the AI does not choose who the bot follows.

## Owner-only IM commands

Set `OWNER_UUID` to your avatar UUID. Then IM the bot:

```text
!help
!status
!follow on
!follow off
!follow distance 3
!ai on
!ai off
!provider OLLAMA
!provider SOJI
!provider AUTO
!model qwen3-airoguelite-fast:latest
!action sit
!action stand
```

Provider/model/follow changes made by IM last only for the current run; `.env` remains the source of truth when the bot restarts.

## Nearby chat

Nearby-chat AI replies are deliberately disabled by default:

```ini
RESPOND_TO_LOCAL_CHAT=false
```

To enable them:

```ini
RESPOND_TO_LOCAL_CHAT=true
LOCAL_CHAT_REQUIRE_NAME=true
```

With `LOCAL_CHAT_REQUIRE_NAME=true`, the bot replies only when its first name appears in the nearby message.

## Persona

Edit `persona.txt` to define how the avatar talks and behaves. The action/JSON protocol is kept in code so persona edits do not accidentally break the control format.

## Soji request shape

Soji is treated as an OpenAI-compatible chat endpoint. Requests include:

- `Authorization: Bearer <SOJI_API_KEY>` when a key is configured
- `Content-Type: application/json`
- `User-Agent: starlablood/1.0` by default

If your Soji URL already ends in `/v1/chat/completions`, the bot uses it as-is; otherwise it appends that path.

## No-surprises audit

Read [`TRANSPARENCY.md`](TRANSPARENCY.md). It lists every intended outbound destination and what is deliberately not in this project.
