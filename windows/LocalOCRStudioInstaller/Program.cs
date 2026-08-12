using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Principal;
using System.Text;
using System.Windows.Forms;

internal static class Program
{
    private const string ServiceName = "LocalOCRStudio";
    private const string ServiceDisplayName = "Local OCR Studio";
    private const string ServiceDescription = "Runs the Local OCR Studio web application in the background.";

    private static readonly string[] InstallerArgs = { "--install", "--uninstall", "--repair" };

    private static void Main(string[] args)
    {
        if (args.Length > 0)
        {
            var command = args[0].ToLowerInvariant();
            if (command == "--install")
            {
                RunElevatedCommand(InstallService);
                return;
            }
            if (command == "--uninstall")
            {
                RunElevatedCommand(UninstallService);
                return;
            }
            if (command == "--repair")
            {
                RunElevatedCommand(RepairService);
                return;
            }
        }

    Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);

        var root = GetProjectRoot();
        var servicePath = Path.Combine(root, "service", "LocalOCRStudioService.exe");

        var message = new StringBuilder();
        message.AppendLine("Local OCR Studio Service Installer");
        message.AppendLine();
        message.AppendLine("Choose an action:");
        message.AppendLine("- Install the service");
        message.AppendLine("- Repair installation");
        message.AppendLine("- Uninstall the service");
        message.AppendLine();
        message.AppendLine("The service executable must exist at:");
        message.AppendLine(servicePath);

        var result = MessageBox.Show(
            message.ToString(),
            "Local OCR Studio Installer",
            MessageBoxButtons.YesNoCancel,
            MessageBoxIcon.Question,
            MessageBoxDefaultButton.Button1,
            MessageBoxOptions.DefaultDesktopOnly);

        if (result == DialogResult.Yes)
        {
            RunElevatedCommand(InstallService);
        }
        else if (result == DialogResult.No)
        {
            RunElevatedCommand(UninstallService);
        }
    }

    private static void RunElevatedCommand(Action command)
    {
        if (!IsElevated())
        {
            var executable = Process.GetCurrentProcess().MainModule?.FileName;
            if (executable is null)
            {
                MessageBox.Show("Unable to determine the installer executable path.");
                return;
            }

            var arguments = string.Join(' ', Environment.GetCommandLineArgs().Skip(1).Select(QuoteArgument));
            var startInfo = new ProcessStartInfo(executable)
            {
                Verb = "runas",
                Arguments = arguments,
                UseShellExecute = true,
            };
            try
            {
                Process.Start(startInfo);
            }
            catch (System.ComponentModel.Win32Exception ex)
            {
                MessageBox.Show($"Elevation required: {ex.Message}", "Local OCR Studio Installer", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            return;
        }

        command();
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

    private static void InstallService()
    {
        var root = GetProjectRoot();
        var serviceExe = Path.Combine(root, "service", "LocalOCRStudioService.exe");
        if (!File.Exists(serviceExe))
        {
            MessageBox.Show($"Service executable not found:\n{serviceExe}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        var process = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = serviceExe,
                Arguments = "--install",
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
            }
        };

        process.Start();
        var output = process.StandardOutput.ReadToEnd();
        var error = process.StandardError.ReadToEnd();
        process.WaitForExit();

        if (process.ExitCode != 0)
        {
            MessageBox.Show($"Install failed:\n{error}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        MessageBox.Show("Service installed and started.", "Success", MessageBoxButtons.OK, MessageBoxIcon.Information);
    }

    private static void UninstallService()
    {
        var root = GetProjectRoot();
        var serviceExe = Path.Combine(root, "service", "LocalOCRStudioService.exe");
        if (!File.Exists(serviceExe))
        {
            MessageBox.Show($"Service executable not found:\n{serviceExe}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        var process = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = serviceExe,
                Arguments = "--uninstall",
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
            }
        };

        process.Start();
        var output = process.StandardOutput.ReadToEnd();
        var error = process.StandardError.ReadToEnd();
        process.WaitForExit();

        if (process.ExitCode != 0)
        {
            MessageBox.Show($"Uninstall failed:\n{error}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        MessageBox.Show("Service uninstalled.", "Success", MessageBoxButtons.OK, MessageBoxIcon.Information);
    }

    private static void RepairService()
    {
        UninstallService();
        InstallService();
    }

    private static string GetProjectRoot()
    {
        var executableDirectory = Path.GetDirectoryName(Process.GetCurrentProcess().MainModule?.FileName) ?? ".";
        executableDirectory = Path.GetFullPath(executableDirectory);

        if (File.Exists(Path.Combine(executableDirectory, "service", "LocalOCRStudioService.exe")))
        {
            return executableDirectory;
        }

        var parent = Path.GetFullPath(Path.Combine(executableDirectory, ".."));
        if (File.Exists(Path.Combine(parent, "service", "LocalOCRStudioService.exe")))
        {
            return parent;
        }

        var grandParent = Path.GetFullPath(Path.Combine(parent, ".."));
        if (File.Exists(Path.Combine(grandParent, "service", "LocalOCRStudioService.exe")))
        {
            return grandParent;
        }

        var greatGrandParent = Path.GetFullPath(Path.Combine(grandParent, ".."));
        if (File.Exists(Path.Combine(greatGrandParent, "service", "LocalOCRStudioService.exe")))
        {
            return greatGrandParent;
        }

        return executableDirectory;
    }
}
