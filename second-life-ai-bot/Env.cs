namespace SecondLifeAiBot;

internal static class Env
{
    public static void Load(string path = ".env")
    {
        if (!File.Exists(path)) return;

        foreach (var raw in File.ReadAllLines(path))
        {
            var line = raw.Trim();
            if (line.Length == 0 || line.StartsWith('#')) continue;

            var equals = line.IndexOf('=');
            if (equals <= 0) continue;

            var key = line[..equals].Trim();
            var value = line[(equals + 1)..].Trim();

            if ((value.StartsWith('"') && value.EndsWith('"')) ||
                (value.StartsWith('\'') && value.EndsWith('\'')))
            {
                value = value[1..^1];
            }

            if (Environment.GetEnvironmentVariable(key) is null)
                Environment.SetEnvironmentVariable(key, value);
        }
    }

    public static string Get(string key, string fallback = "") =>
        Environment.GetEnvironmentVariable(key)?.Trim() is { Length: > 0 } value ? value : fallback;

    public static bool Bool(string key, bool fallback = false)
    {
        var value = Get(key);
        return value.Length == 0 ? fallback :
            value.Equals("1") || value.Equals("true", StringComparison.OrdinalIgnoreCase) ||
            value.Equals("yes", StringComparison.OrdinalIgnoreCase) ||
            value.Equals("on", StringComparison.OrdinalIgnoreCase);
    }

    public static int Int(string key, int fallback)
    {
        return int.TryParse(Get(key), out var value) ? value : fallback;
    }
}
