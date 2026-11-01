// MoodCafe.exe: starts the Mood Cafe kiosk (app.py) with the project's .venv, without a console window.
// Build: launcher\build.bat
using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Windows.Forms;

[assembly: System.Reflection.AssemblyTitle("Mood Cafe")]
[assembly: System.Reflection.AssemblyProduct("Mood Cafe")]
[assembly: System.Reflection.AssemblyVersion("1.0.0.0")]

static class MoodCafeLauncher
{
    [STAThread]
    static int Main()
    {
        string dir = AppDomain.CurrentDomain.BaseDirectory;
        string pythonw = Path.Combine(dir, @".venv\Scripts\pythonw.exe");
        string app = Path.Combine(dir, "app.py");
        string log = Path.Combine(dir, "moodcafe.log");

        if (!File.Exists(app))
            return Warn("app.py was not found. Keep MoodCafe.exe inside the MoodCafe folder " +
                        "(use a shortcut to start it from the Desktop).");
        if (!File.Exists(pythonw) || !File.Exists(Path.Combine(dir, @"models\expression\model.safetensors")))
            return Warn("Mood Cafe is not set up yet.\n\nDouble-click INSTALL_WINDOWS.bat (needs internet once), " +
                        "then open MoodCafe.exe again.");

        // Pass any arguments through, e.g. MoodCafe.exe --demo data\demo
        string extra = string.Join(" ", Environment.GetCommandLineArgs().Skip(1).Select(a => "\"" + a + "\""));
        Process process;
        try
        {
            process = Process.Start(new ProcessStartInfo(pythonw, "\"" + app + "\" " + extra)
            {
                WorkingDirectory = dir,
                UseShellExecute = false,
            });
        }
        catch (Exception ex)
        {
            return Warn("Could not start Python: " + ex.Message);
        }

        // A crash right at start (broken install) would otherwise be silent.
        if (process.WaitForExit(8000) && process.ExitCode != 0 && File.Exists(log))
        {
            string[] lines;
            using (var stream = new FileStream(log, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
            using (var reader = new StreamReader(stream))
                lines = reader.ReadToEnd().Split('\n');
            string tail = string.Join("\n", lines.Skip(Math.Max(0, lines.Length - 12)));
            if (tail.Trim().Length > 0)
                return Warn("Mood Cafe closed unexpectedly:\n\n" + tail + "\n\nLog: " + log);
        }
        return 0;
    }

    static int Warn(string message)
    {
        MessageBox.Show(message, "Mood Cafe", MessageBoxButtons.OK, MessageBoxIcon.Information);
        return 1;
    }
}
