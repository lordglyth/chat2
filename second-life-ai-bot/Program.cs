using LibreMetaverse;
using SecondLifeAiBot;

Env.Load();

var firstName = Env.Get("SL_FIRST_NAME");
var lastName = Env.Get("SL_LAST_NAME", "Resident");
var password = Env.Get("SL_PASSWORD");

if (string.IsNullOrWhiteSpace(firstName) || string.IsNullOrWhiteSpace(password))
{
    Console.Error.WriteLine("Missing SL_FIRST_NAME or SL_PASSWORD. Copy .env.example to .env and fill in your bot account.");
    return 1;
}

var client = new GridClient();
var ai = new AiClient();
var brain = new BotBrain(client, ai);
var localChatEnabled = Env.Bool("RESPOND_TO_LOCAL_CHAT", false);
var localChatMustMention = Env.Bool("LOCAL_CHAT_REQUIRE_NAME", true);
var aiEnabled = true;
var ownerIdText = Env.Get("OWNER_UUID");
var ownerId = UUID.Zero;
if (!string.IsNullOrWhiteSpace(ownerIdText) && !UUID.TryParse(ownerIdText, out ownerId))
{
    Console.Error.WriteLine("OWNER_UUID is not a valid UUID.");
    return 1;
}

var follower = new OwnerFollower(client, ownerId);
var shutdown = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);

client.Network.LoginProgress += (_, e) => Console.WriteLine($"[LOGIN] {e.Status}: {e.Message}");
client.Network.Disconnected += (_, e) =>
{
    Console.WriteLine($"[DISCONNECTED] {e.Reason}: {e.Message}");
    shutdown.TrySetResult(true);
};

client.Self.IM += (_, e) => _ = HandleImAsync(e);
client.Self.ChatFromSimulator += (_, e) => _ = HandleLocalChatAsync(e);

Console.CancelKeyPress += (_, e) =>
{
    e.Cancel = true;
    shutdown.TrySetResult(true);
};

Console.WriteLine("Second Life AI Bot 1.1");
Console.WriteLine($"Provider: {AiClient.Name(ai.Provider)}");
Console.WriteLine($"Local chat AI: {(localChatEnabled ? "ON" : "OFF")}");
Console.WriteLine("Logging in...");

var loginParams = client.Network.DefaultLoginParams(firstName, lastName, password, "SecondLifeAIBot", "1.1.0");
using var loginCts = new CancellationTokenSource(TimeSpan.FromSeconds(45));

try
{
    var success = await client.Network.LoginAsync(loginParams, loginCts.Token);
    if (!success)
    {
        Console.Error.WriteLine($"Login failed: {client.Network.LoginMessage}");
        return 1;
    }
}
catch (OperationCanceledException)
{
    Console.Error.WriteLine("Second Life login timed out.");
    return 1;
}

follower.Start();
Console.WriteLine($"Logged in as {firstName} {lastName} in {client.Network.CurrentSim?.Name ?? "unknown"}.");
Console.WriteLine("Ctrl+C to log out.");
await shutdown.Task;

follower.Stop();
if (client.Network.Connected)
    client.Network.Logout();
return 0;

async Task HandleImAsync(InstantMessageEventArgs e)
{
    if (e.IM.FromAgentID == client.Self.AgentID) return;

    var fromId = e.IM.FromAgentID;
    var fromName = e.IM.FromAgentName;
    var message = e.IM.Message.Trim();
    if (message.Length == 0) return;

    Console.WriteLine($"[IM] {fromName}: {message}");

    if (message.StartsWith('!'))
    {
        var commandReply = HandleAdminCommand(fromId, message);
        client.Self.InstantMessage(fromId, commandReply);
        return;
    }

    if (!aiEnabled)
    {
        client.Self.InstantMessage(fromId, "AI control is currently off.");
        return;
    }

    try
    {
        var reply = await brain.ThinkAsync(fromName, message, "instant message");
        brain.ExecuteAction(reply.Action);
        if (!string.IsNullOrWhiteSpace(reply.Say))
            client.Self.InstantMessage(fromId, reply.Say);
    }
    catch (Exception ex)
    {
        Console.WriteLine($"[AI ERROR] {ex.Message}");
        client.Self.InstantMessage(fromId, "My AI connection hit an error. Check the bot console.");
    }
}

async Task HandleLocalChatAsync(ChatEventArgs e)
{
    if (!localChatEnabled || !aiEnabled) return;
    if (e.SourceID == client.Self.AgentID || string.IsNullOrWhiteSpace(e.Message)) return;

    if (localChatMustMention)
    {
        var botName = firstName;
        if (!e.Message.Contains(botName, StringComparison.OrdinalIgnoreCase)) return;
    }

    Console.WriteLine($"[CHAT] {e.FromName}: {e.Message}");

    try
    {
        var reply = await brain.ThinkAsync(e.FromName, e.Message, "nearby chat");
        brain.ExecuteAction(reply.Action);
        if (!string.IsNullOrWhiteSpace(reply.Say))
            client.Self.Chat(reply.Say, 0, ChatType.Normal);
    }
    catch (Exception ex)
    {
        Console.WriteLine($"[AI ERROR] local chat: {ex.Message}");
    }
}

string HandleAdminCommand(UUID sender, string raw)
{
    if (ownerId == UUID.Zero)
        return "Admin commands are disabled until OWNER_UUID is set in .env.";
    if (sender != ownerId)
        return "That command is owner-only.";

    var pieces = raw.Split(' ', 3, StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
    var cmd = pieces[0].ToLowerInvariant();

    switch (cmd)
    {
        case "!help":
            return "Owner commands: !status, !follow on|off, !follow distance <meters>, !ai on|off, !provider OLLAMA|SOJI|AUTO, !model <name>, !action none|sit|stand|dance|fly|walk|jump";

        case "!status":
            return $"AI={(aiEnabled ? "ON" : "OFF")}; provider={AiClient.Name(ai.Provider)}; follow={(follower.Enabled ? "ON" : "OFF")}; owner_visible={(follower.TargetVisible ? "YES" : "NO")}; follow_distance={follower.FollowDistance:0.0}m; ollama_model={ai.OllamaModel}; soji_model={ai.SojiModel}; region={client.Network.CurrentSim?.Name ?? "unknown"}; pos={client.Self.SimPosition}";

        case "!follow":
            if (pieces.Length < 2)
                return $"Follow is {(follower.Enabled ? "ON" : "OFF")} at {follower.FollowDistance:0.0}m. Usage: !follow on|off OR !follow distance <meters>.";

            if (pieces[1].Equals("on", StringComparison.OrdinalIgnoreCase))
            {
                follower.SetEnabled(true);
                return $"Following you at {follower.FollowDistance:0.0}m.";
            }

            if (pieces[1].Equals("off", StringComparison.OrdinalIgnoreCase))
            {
                follower.SetEnabled(false);
                return "Following is off.";
            }

            if (pieces[1].Equals("distance", StringComparison.OrdinalIgnoreCase))
            {
                if (pieces.Length < 3 || !float.TryParse(pieces[2], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var requestedDistance))
                    return "Usage: !follow distance <meters> (1.5 to 20).";

                var actual = follower.SetDistance(requestedDistance);
                return $"Follow distance set to {actual:0.0}m.";
            }

            if (float.TryParse(pieces[1], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var shortDistance))
            {
                var actual = follower.SetDistance(shortDistance);
                return $"Follow distance set to {actual:0.0}m.";
            }

            return "Usage: !follow on|off OR !follow distance <meters>.";

        case "!ai":
            if (pieces.Length < 2) return "Usage: !ai on|off";
            if (pieces[1].Equals("on", StringComparison.OrdinalIgnoreCase)) aiEnabled = true;
            else if (pieces[1].Equals("off", StringComparison.OrdinalIgnoreCase)) aiEnabled = false;
            else return "Usage: !ai on|off";
            return $"AI control {(aiEnabled ? "ON" : "OFF")}.";

        case "!provider":
            if (pieces.Length < 2) return "Usage: !provider OLLAMA|SOJI|AUTO";
            try
            {
                ai.Provider = AiClient.ParseProvider(pieces[1]);
                return $"Provider set to {AiClient.Name(ai.Provider)} for this run.";
            }
            catch (Exception ex)
            {
                return ex.Message;
            }

        case "!model":
            if (pieces.Length < 2) return "Usage: !model <model-name>";
            if (ai.Provider == AiProvider.Soji)
                ai.SojiModel = raw[(raw.IndexOf(' ') + 1)..].Trim();
            else
                ai.OllamaModel = raw[(raw.IndexOf(' ') + 1)..].Trim();
            return $"Model updated for this run: {(ai.Provider == AiProvider.Soji ? ai.SojiModel : ai.OllamaModel)}";

        case "!action":
            if (pieces.Length < 2) return "Usage: !action none|sit|stand|dance|fly|walk|jump";
            return $"Action result: {brain.ExecuteAction(pieces[1])}";

        default:
            return "Unknown owner command. Use !help.";
    }
}
