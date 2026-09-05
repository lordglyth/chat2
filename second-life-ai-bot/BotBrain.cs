using System.Text.Json;
using LibreMetaverse;

namespace SecondLifeAiBot;

internal sealed record BrainReply(string Say, string Action);

internal sealed class BotBrain
{
    private readonly GridClient _client;
    private readonly AiClient _ai;
    private readonly string _persona;
    private readonly SemaphoreSlim _gate = new(1, 1);
    private readonly int _maxOutputChars;

    public BotBrain(GridClient client, AiClient ai)
    {
        _client = client;
        _ai = ai;
        _maxOutputChars = Env.Int("MAX_OUTPUT_CHARS", 900);

        var personaFile = Env.Get("PERSONA_FILE", "persona.txt");
        _persona = File.Exists(personaFile)
            ? File.ReadAllText(personaFile).Trim()
            : "You are an autonomous AI avatar in Second Life. Be conversational and stay in character.";
    }

    public async Task<BrainReply> ThinkAsync(string speaker, string message, string channel, CancellationToken ct = default)
    {
        await _gate.WaitAsync(ct);
        try
        {
            var sim = _client.Network.CurrentSim?.Name ?? "unknown";
            var position = _client.Self.SimPosition;

            var system = $"""
{_persona}

You control a Second Life bot. Reply ONLY with one JSON object, no markdown and no commentary.
Schema:
{{"say":"text to send back","action":"none|sit|stand|dance|fly|walk|jump"}}

Rules:
- The action field is optional in spirit but must always be present; use "none" when no action is needed.
- Never invent an action outside the allowed action list.
- Keep say under {_maxOutputChars} characters.
- You may converse naturally. Do not mention this JSON protocol to residents.
""";

            var user = $"""
Channel: {channel}
Speaker: {speaker}
Region: {sim}
Bot position: {position}
Message: {message}
""";

            var raw = await _ai.CompleteAsync(system, user, ct);
            var reply = ParseReply(raw);
            return reply with { Say = Truncate(reply.Say, _maxOutputChars) };
        }
        finally
        {
            _gate.Release();
        }
    }

    public string ExecuteAction(string action)
    {
        var normalized = action.Trim().ToLowerInvariant();
        try
        {
            switch (normalized)
            {
                case "":
                case "none":
                    return "none";
                case "sit":
                    _client.Self.SitOnGround();
                    return "sit";
                case "stand":
                    _client.Self.Stand();
                    return "stand";
                case "dance":
                    _client.Self.AnimationStart(Animations.DANCE1, true);
                    return "dance";
                case "fly":
                    _client.Self.Fly(true);
                    return "fly";
                case "walk":
                    _client.Self.Fly(false);
                    return "walk";
                case "jump":
                    _client.Self.Jump(true);
                    _ = Task.Delay(500).ContinueWith(_ => _client.Self.Jump(false));
                    return "jump";
                default:
                    Console.WriteLine($"[ACTION BLOCKED] AI requested unsupported action: {action}");
                    return "blocked";
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[ACTION ERROR] {normalized}: {ex.Message}");
            return "error";
        }
    }

    private static BrainReply ParseReply(string raw)
    {
        var jsonText = ExtractJson(raw);
        using var json = JsonDocument.Parse(jsonText);
        var root = json.RootElement;

        var say = root.TryGetProperty("say", out var sayElement) ? sayElement.GetString() ?? "" : "";
        var action = root.TryGetProperty("action", out var actionElement) ? actionElement.GetString() ?? "none" : "none";
        return new BrainReply(say.Trim(), action.Trim());
    }

    private static string ExtractJson(string raw)
    {
        var text = raw.Trim();
        if (text.StartsWith("```"))
        {
            var firstNewline = text.IndexOf('\n');
            var lastFence = text.LastIndexOf("```", StringComparison.Ordinal);
            if (firstNewline >= 0 && lastFence > firstNewline)
                text = text[(firstNewline + 1)..lastFence].Trim();
        }

        var start = text.IndexOf('{');
        var end = text.LastIndexOf('}');
        if (start < 0 || end <= start)
            throw new JsonException("AI response did not contain a JSON object");

        return text[start..(end + 1)];
    }

    private static string Truncate(string value, int max) => value.Length <= max ? value : value[..max];
}
