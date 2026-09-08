using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

class Launcher {
    [STAThread]
    static int Main(string[] args) {
        string root = AppDomain.CurrentDomain.BaseDirectory;
        string python = Path.Combine(root, ".venv", "Scripts", "pythonw.exe");
        string module = Path.Combine(root, "src", "cad_workbench", "desktop.py");
        bool check = args.Length == 1 && args[0] == "--check";
        if (!File.Exists(python) || !File.Exists(module)) {
            if (!check) MessageBox.Show("Keep V8_CAD.exe inside the V8_CAD project folder with its .venv and src folders.", "V8_CAD");
            return 1;
        }
        if (check) return 0;
        try {
            var info = new ProcessStartInfo(python, "-m cad_workbench.desktop");
            info.WorkingDirectory = root;
            info.UseShellExecute = false;
            info.CreateNoWindow = true;
            info.EnvironmentVariables["PYTHONPATH"] = Path.Combine(root, "src");
            Process.Start(info);
            return 0;
        } catch (Exception e) {
            MessageBox.Show(e.Message, "V8_CAD startup error");
            return 2;
        }
    }
}
