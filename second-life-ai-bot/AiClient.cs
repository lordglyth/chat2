using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

namespace SecondLifeAiBot;

internal enum AiProvider
{
    Ollama,
    Soji,
    Auto
}

internal sealed class AiClient
{
    private readonly HttpClient _http = new() { Timeout = TimeSpan.FromSeconds(90) };

    public AiProvider Provider { get; set; }
    public string OllamaModel { get; set; }
    public string SojiModel { get; set; }

    public AiClient()
    {
        Provider = ParseProvider(Env.Get("AI_PROVIDER", "OLLAMA"));
        OllamaModel = Env.Get("OLLAMA_MODEL", "qwen3-airoguelite-fast:latest");
        SojiModel = Env.Get("SOJI_MODEL", "");
    }

    public async Task<string> CompleteAsync(string systemPrompt, string userPrompt, CancellationToken ct = default)
    {
        return Provider switch
        {
            AiProvider.Ollama => await CallOllamaAsync(systemPrompt, userPrompt, ct),
            AiProvider.Soji => await CallSojiAsync(systemPrompt, userPrompt, ct),
            AiProvider.Auto => await CallAutoAsync(systemPrompt, userPrompt, ct),
            _ => throw new InvalidOperationException("Unknown AI provider")
        };
    }

    private async Task<string> CallAutoAsync(string systemPrompt, string userPrompt, CancellationToken ct)
    {
        var order = Env.Get("AUTO_ORDER", "OLLAMA,SOJI")
            .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);

        var errors = new List<string>();
        foreach (var provider in order)
        {
            try
            {
                if (provider.Equals("OLLAMA", StringComparison.OrdinalIgnoreCase))
                    return await CallOllamaAsync(systemPrompt, userPrompt, ct);
                if (provider.Equals("SOJI", StringComparison.OrdinalIgnoreCase))
                    return await CallSojiAsync(systemPrompt, userPrompt, ct);
            }
            catch (Exception ex)
            {
                errors.Add($"{provider}: {ex.Message}");
            }
        }

        throw new InvalidOperationException("AUTO providers failed: " + string.Join(" | ", errors));
    }

    private Task<string> CallOllamaAsync(string systemPrompt, string userPrompt, CancellationToken ct)
    {
        var endpoint = Env.Get("OLLAMA_URL", "http://127.0.0.1:11434/v1/chat/completions");
        return CallOpenAiCompatibleAsync(endpoint, OllamaModel, null, "SecondLifeAIBot/1.0", systemPrompt, userPrompt, ct);
    }

    private Task<string> CallSojiAsync(string systemPrompt, string userPrompt, CancellationToken ct)
    {
        var baseUrl = Env.Get("SOJI_BASE_URL");
        if (string.IsNullOrWhiteSpace(baseUrl))
            throw new InvalidOperationException("SOJI_BASE_URL is not configured");
        if (string.IsNullOrWhiteSpace(SojiModel))
            throw new InvalidOperationException("SOJI_MODEL is not configured");

        var endpoint = NormalizeChatEndpoint(baseUrl);
        var apiKey = Env.Get("SOJI_API_KEY");
        var userAgent = Env.Get("SOJI_USER_AGENT", "starlablood/1.0");
        return CallOpenAiCompatibleAsync(endpoint, SojiModel, apiKey, userAgent, systemPrompt, userPrompt, ct);
    }

    private async Task<string> CallOpenAiCompatibleAsync(
        string endpoint,
        string model,
        string? apiKey,
        string userAgent,
        string systemPrompt,
        string userPrompt,
        CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(model))
            throw new InvalidOperationException("AI model is blank");

        var payload = new
        {
            model,
            messages = new object[]
            {
                new { role = "system", content = systemPrompt },
                new { role = "user", content = userPrompt }
            },
            temperature = 0.7,
            stream = false
        };

        using var request = new HttpRequestMessage(HttpMethod.Post, endpoint);
        request.Headers.UserAgent.ParseAdd(userAgent);
        if (!string.IsNullOrWhiteSpace(apiKey))
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);
        request.Content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");

        using var response = await _http.SendAsync(request, ct);
        var body = await response.Content.ReadAsStringAsync(ct);
        if (!response.IsSuccessStatusCode)
            throw new HttpRequestException($"AI endpoint returned {(int)response.StatusCode}: {Trim(body, 300)}");

        using var json = JsonDocument.Parse(body);
        var content = json.RootElement
            .GetProperty("choices")[0]
            .GetProperty("message")
            .GetProperty("content")
            .GetString();

        return string.IsNullOrWhiteSpace(content)
            ? throw new InvalidOperationException("AI endpoint returned an empty response")
            : content.Trim();
    }

    public static AiProvider ParseProvider(string value) => value.Trim().ToUpperInvariant() switch
    {
        "OLLAMA" or "LOCAL" => AiProvider.Ollama,
        "SOJI" => AiProvider.Soji,
        "AUTO" => AiProvider.Auto,
        _ => throw new ArgumentException("AI_PROVIDER must be OLLAMA, SOJI, or AUTO")
    };

    public static string Name(AiProvider provider) => provider switch
    {
        AiProvider.Ollama => "OLLAMA",
        AiProvider.Soji => "SOJI",
        AiProvider.Auto => "AUTO",
        _ => "UNKNOWN"
    };

    private static string NormalizeChatEndpoint(string baseUrl)
    {
        var clean = baseUrl.Trim().TrimEnd('/');
        return clean.EndsWith("/v1/chat/completions", StringComparison.OrdinalIgnoreCase)
            ? clean
            : clean + "/v1/chat/completions";
    }

    private static string Trim(string value, int max) => value.Length <= max ? value : value[..max] + "...";
}
