using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Principal;
using System.Text;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

internal static class Program
{
    private const string ServiceName = "LocalOCRStudio";
    private const string ServiceDisplayName = "Local OCR Studio";
    private const string ServiceDescription = "Runs the Local OCR Studio web application in the background.";
    private static readonly string[] ServiceCommands = { "--install", "--uninstall", "--start", "--stop", "--status" };

    private static async Task<int> Main(string[] args)
    {
        if (args.Length > 0 && ServiceCommands.Contains(args[0], StringComparer.OrdinalIgnoreCase))
        {
            return await RunServiceCommandAsync(args);
        }

        var hostBuilder = Host.CreateDefaultBuilder(args)
            .UseWindowsService(options => { options.ServiceName = ServiceName; })
            .ConfigureServices((context, services) =>
            {
                services.AddHostedService<OcrMonitorService>();
            })
            .ConfigureLogging(logging =>
            {
                logging.ClearProviders();
                logging.AddConsole();
            });

        var host = hostBuilder.Build();
        await host.RunAsync();
        return 0;
    }

    private static async Task<int> RunServiceCommandAsync(string[] args)
    {
        if (!IsElevated())
        {
            return RelaunchWithElevation(args);
        }

        var command = args[0].ToLowerInvariant();
        return command switch
        {
            "--install" => InstallService(),
            "--uninstall" => UninstallService(),
            "--start" => ControlService("start"),
            "--stop" => ControlService("stop"),
            "--status" => QueryServiceStatus(),
            _ => PrintUsage(),
        };
    }

    private static int InstallService()
    {
        var executable = GetChainedExecutablePath();
        if (RunScCommand($"create {ServiceName} binPath= \"{executable}\" start= auto DisplayName= \"{ServiceDisplayName}\"") != 0)
        {
            return 1;
        }

        RunScCommand($"description {ServiceName} \"{ServiceDescription}\"");
        RunScCommand($"failure {ServiceName} reset= 86400 actions= restart/5000/restart/5000/restart/5000");
        return ControlService("start");
    }

    private static int UninstallService()
    {
        ControlService("stop");
        return RunScCommand($"delete {ServiceName}");
    }

    private static int ControlService(string action)
    {
        return RunScCommand($"{action} {ServiceName}");
    }

    private static int QueryServiceStatus()
    {
        return RunScCommand($"query {ServiceName}");
    }

    private static int PrintUsage()
    {
        Console.WriteLine("Local OCR Studio Service wrapper commands:");
        Console.WriteLine("  --install   Install and start the Windows service");
        Console.WriteLine("  --uninstall Stop and remove the Windows service");
        Console.WriteLine("  --start     Start the installed Windows service");
        Console.WriteLine("  --stop      Stop the installed Windows service");
        Console.WriteLine("  --status    Query the installed Windows service");
        return 0;
    }

    private static bool IsElevated()
    {
        try
        {
            using var identity = WindowsIdentity.GetCurrent();
            var principal = new WindowsPrincipal(identity);
            return principal.IsInRole(WindowsBuiltInRole.Administrator);
        }
        catch
        {
            return false;
        }
    }

    private static int RelaunchWithElevation(string[] args)
    {
        var executable = GetChainedExecutablePath();
        var quotedArguments = string.Join(' ', args.Select(QuoteArgument));

        var startInfo = new ProcessStartInfo(executable)
        {
            Verb = "runas",
            Arguments = quotedArguments,
            UseShellExecute = true,
        };

        try
        {
            Process.Start(startInfo);
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Elevation required to perform the operation: {ex.Message}");
            return 1;
        }
    }

    private static string GetChainedExecutablePath()
    {
        var executablePath = Process.GetCurrentProcess().MainModule?.FileName;
        return executablePath ?? throw new InvalidOperationException("Unable to determine the current executable path.");
    }

    private static int RunScCommand(string arguments)
    {
        using var process = new Process();
        process.StartInfo.FileName = "sc.exe";
        process.StartInfo.Arguments = arguments;
        process.StartInfo.RedirectStandardOutput = true;
        process.StartInfo.RedirectStandardError = true;
        process.StartInfo.UseShellExecute = false;
        process.StartInfo.CreateNoWindow = true;
        process.Start();
        var stdout = process.StandardOutput.ReadToEnd();
        var stderr = process.StandardError.ReadToEnd();
        process.WaitForExit();
        if (!string.IsNullOrWhiteSpace(stdout))
        {
            Console.WriteLine(stdout.Trim());
        }

        if (!string.IsNullOrWhiteSpace(stderr))
        {
            Console.Error.WriteLine(stderr.Trim());
        }

        return process.ExitCode;
    }

    private static string QuoteArgument(string value)
    {
        return value.Contains(' ') || value.Contains('"') ? '"' + value.Replace("\"", "\\\"") + '"' : value;
    }
}
