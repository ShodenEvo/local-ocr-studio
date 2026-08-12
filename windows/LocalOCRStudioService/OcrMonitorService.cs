using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

internal sealed class OcrMonitorService : BackgroundService
{
    private readonly ILogger<OcrMonitorService> _logger;
    private Process? _process;

    public OcrMonitorService(ILogger<OcrMonitorService> logger)
    {
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var root = ResolveProjectRoot();
        var pythonExe = Path.Combine(root, "venv", "Scripts", "python.exe");
        var appEntry = Path.Combine(root, "app", "main.py");
        var logsDir = Path.Combine(root, "logs");
        Directory.CreateDirectory(logsDir);
        var logPath = Path.Combine(logsDir, "service.log");

        if (!File.Exists(pythonExe))
        {
            throw new FileNotFoundException("Virtual environment Python not found.", pythonExe);
        }

        if (!File.Exists(appEntry))
        {
            throw new FileNotFoundException("Application entry point not found.", appEntry);
        }

        var host = Environment.GetEnvironmentVariable("OCR_HOST") ?? "127.0.0.1";
        var port = Environment.GetEnvironmentVariable("OCR_PORT") ?? "8095";
        var restartAttempts = 0;
        var restartWindowStart = DateTimeOffset.UtcNow;
        const int maxRestartAttempts = 5;
        const int restartWindowSeconds = 300;

        await using var logStream = new FileStream(logPath, FileMode.Append, FileAccess.Write, FileShare.ReadWrite);
        await using var logWriter = new StreamWriter(logStream, new UTF8Encoding(false)) { AutoFlush = true };

        while (!stoppingToken.IsCancellationRequested)
        {
            if (DateTimeOffset.UtcNow - restartWindowStart > TimeSpan.FromSeconds(restartWindowSeconds))
            {
                restartAttempts = 0;
                restartWindowStart = DateTimeOffset.UtcNow;
            }

            _logger.LogInformation("Starting OCR server process.");
            WriteLog(logWriter, "Starting OCR server process.");

            using var process = CreateProcess(pythonExe, root, host, port);
            _process = process;
            process.OutputDataReceived += (sender, eventArgs) => WriteProcessLine(logWriter, eventArgs.Data);
            process.ErrorDataReceived += (sender, eventArgs) => WriteProcessLine(logWriter, eventArgs.Data);
            process.Start();
            process.BeginOutputReadLine();
            process.BeginErrorReadLine();

            var exitTask = WaitForExitAsync(process, stoppingToken);
            await Task.WhenAny(exitTask, Task.Delay(Timeout.Infinite, stoppingToken));

            if (stoppingToken.IsCancellationRequested)
            {
                break;
            }

            await exitTask;

            if (process.ExitCode == 0)
            {
                _logger.LogInformation("OCR server process exited normally.");
                WriteLog(logWriter, "OCR server process exited normally.");
                break;
            }

            restartAttempts++;
            var message = $"OCR server exited unexpectedly with code {process.ExitCode}. Restart attempt {restartAttempts} of {maxRestartAttempts}.";
            _logger.LogWarning(message);
            WriteLog(logWriter, message);

            if (restartAttempts > maxRestartAttempts)
            {
                var failureMessage = "Maximum restart attempts exceeded. Service will stop.";
                _logger.LogError(failureMessage);
                WriteLog(logWriter, failureMessage);
                throw new InvalidOperationException(failureMessage);
            }

            try
            {
                await Task.Delay(TimeSpan.FromSeconds(5), stoppingToken);
            }
            catch (TaskCanceledException)
            {
                break;
            }
        }
    }

    public override async Task StopAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("Stopping OCR service monitor.");
        if (_process != null && !_process.HasExited)
        {
            try
            {
                _process.Kill(true);
                await _process.WaitForExitAsync(cancellationToken);
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Failed to stop OCR process gracefully.");
            }
        }

        await base.StopAsync(cancellationToken);
    }

    private static Process CreateProcess(string pythonExe, string workingDirectory, string host, string port)
    {
        var processStartInfo = new ProcessStartInfo
        {
            FileName = pythonExe,
            Arguments = $"-m uvicorn app.main:app --host {host} --port {port}",
            WorkingDirectory = workingDirectory,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8,
        };

        foreach (var environmentVariable in Environment.GetEnvironmentVariables().Cast<System.Collections.DictionaryEntry>())
        {
            if (environmentVariable.Key is string key && environmentVariable.Value is string value)
            {
                processStartInfo.Environment[key] = value;
            }
        }

        processStartInfo.Environment["PYTHONUNBUFFERED"] = "1";
        processStartInfo.Environment["PYTHONUTF8"] = "1";
        processStartInfo.Environment["PYTHONIOENCODING"] = "utf-8";

        var easyocrModelDir = Path.Combine(workingDirectory, "models", "easyocr");
        Directory.CreateDirectory(easyocrModelDir);
        processStartInfo.Environment["EASYOCR_MODULE_PATH"] = easyocrModelDir;
        processStartInfo.Environment["MODULE_PATH"] = easyocrModelDir;

        return new Process { StartInfo = processStartInfo, EnableRaisingEvents = true };
    }

    private static async Task WaitForExitAsync(Process process, CancellationToken cancellationToken)
    {
        var tcs = new TaskCompletionSource<object?>();

        void OnExited(object? sender, EventArgs e)
        {
            tcs.TrySetResult(null);
        }

        process.Exited += OnExited;

        using (cancellationToken.Register(() => tcs.TrySetCanceled()))
        {
            try
            {
                await tcs.Task;
            }
            finally
            {
                process.Exited -= OnExited;
            }
        }
    }

    private static void WriteLog(StreamWriter writer, string message)
    {
        var timestamp = DateTimeOffset.Now.ToString("yyyy-MM-dd HH:mm:ss");
        writer.WriteLine($"[{timestamp}] {message}");
    }

    private static void WriteProcessLine(StreamWriter writer, string? line)
    {
        if (string.IsNullOrWhiteSpace(line))
        {
            return;
        }

        WriteLog(writer, line);
    }

    private static string ResolveProjectRoot()
    {
        var executableDirectory = AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        var rootCandidate = Path.GetFullPath(Path.Combine(executableDirectory, ".."));

        if (File.Exists(Path.Combine(executableDirectory, "app", "main.py")) &&
            File.Exists(Path.Combine(executableDirectory, "venv", "Scripts", "python.exe")))
        {
            return executableDirectory;
        }

        if (File.Exists(Path.Combine(rootCandidate, "app", "main.py")) &&
            File.Exists(Path.Combine(rootCandidate, "venv", "Scripts", "python.exe")))
        {
            return rootCandidate;
        }

        return rootCandidate;
    }
}
