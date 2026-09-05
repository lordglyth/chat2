using LibreMetaverse;

namespace SecondLifeAiBot;

internal sealed class OwnerFollower
{
    private readonly GridClient _client;
    private readonly UUID _ownerId;
    private readonly int _updateMs;
    private readonly CancellationTokenSource _cts = new();
    private Task? _loopTask;
    private bool _lastVisible;

    public bool Enabled { get; private set; }
    public bool TargetVisible { get; private set; }
    public float FollowDistance { get; private set; }

    public OwnerFollower(GridClient client, UUID ownerId)
    {
        _client = client;
        _ownerId = ownerId;
        FollowDistance = Math.Clamp(ParseFloat(Env.Get("FOLLOW_DISTANCE_METERS", "3.0"), 3.0f), 1.5f, 20.0f);
        _updateMs = Math.Clamp(Env.Int("FOLLOW_UPDATE_MS", 750), 250, 5000);
        Enabled = ownerId != UUID.Zero && Env.Bool("FOLLOW_OWNER_ON_START", true);
    }

    public void Start()
    {
        if (_loopTask is not null) return;
        _loopTask = Task.Run(() => LoopAsync(_cts.Token));
        Console.WriteLine($"[FOLLOW] {(Enabled ? "ON" : "OFF")}; distance={FollowDistance:0.0}m");
    }

    public void SetEnabled(bool enabled)
    {
        Enabled = enabled && _ownerId != UUID.Zero;
        if (!Enabled)
        {
            TargetVisible = false;
            _client.Self.AutoPilotCancel();
        }

        Console.WriteLine($"[FOLLOW] {(Enabled ? "ON" : "OFF")}");
    }

    public float SetDistance(float meters)
    {
        FollowDistance = Math.Clamp(meters, 1.5f, 20.0f);
        Console.WriteLine($"[FOLLOW] distance={FollowDistance:0.0}m");
        return FollowDistance;
    }

    public void Stop()
    {
        Enabled = false;
        TargetVisible = false;
        _client.Self.AutoPilotCancel();
        _cts.Cancel();
    }

    private async Task LoopAsync(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            try
            {
                if (Enabled && _client.Network.Connected)
                    Tick();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[FOLLOW ERROR] {ex.Message}");
            }

            try
            {
                await Task.Delay(_updateMs, ct);
            }
            catch (OperationCanceledException)
            {
                break;
            }
        }
    }

    private void Tick()
    {
        if (_ownerId == UUID.Zero)
        {
            SetEnabled(false);
            return;
        }

        Simulator? targetSim = null;
        Avatar? targetAvatar = null;

        lock (_client.Network.Simulators)
        {
            foreach (var sim in _client.Network.Simulators)
            {
                var match = sim.ObjectsAvatars.FirstOrDefault(kvp => kvp.Value is not null && kvp.Value.ID == _ownerId);
                if (match.Value is not null)
                {
                    targetSim = sim;
                    targetAvatar = match.Value;
                    break;
                }
            }
        }

        TargetVisible = targetSim is not null && targetAvatar is not null;
        if (TargetVisible != _lastVisible)
        {
            Console.WriteLine(TargetVisible ? "[FOLLOW] Owner acquired." : "[FOLLOW] Owner not currently visible; waiting.");
            _lastVisible = TargetVisible;
        }

        if (!TargetVisible || targetSim is null || targetAvatar is null)
        {
            _client.Self.AutoPilotCancel();
            return;
        }

        var currentSim = _client.Network.CurrentSim;
        if (currentSim is null) return;

        GetGlobal(currentSim, _client.Self.SimPosition, out var selfX, out var selfY, out var selfZ);
        GetGlobal(targetSim, targetAvatar.Position, out var targetX, out var targetY, out var targetZ);

        var dx = targetX - selfX;
        var dy = targetY - selfY;
        var dz = targetZ - selfZ;
        var distance = Math.Sqrt((dx * dx) + (dy * dy) + (dz * dz));

        if (distance <= FollowDistance)
        {
            _client.Self.AutoPilotCancel();
            return;
        }

        _client.Self.AutoPilot(targetX, targetY, targetZ);
    }

    private static void GetGlobal(Simulator sim, Vector3 local, out double x, out double y, out double z)
    {
        Utils.LongToUInts(sim.Handle, out var regionX, out var regionY);
        x = regionX + local.X;
        y = regionY + local.Y;
        z = local.Z;
    }

    private static float ParseFloat(string value, float fallback) =>
        float.TryParse(value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var result)
            ? result
            : fallback;
}
