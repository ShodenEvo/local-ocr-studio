from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import threading
import tkinter as tk
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

from PIL import Image, ImageDraw

try:
    import pystray
except ImportError:
    pystray = None

SERVICE_NAME = "LocalOCRStudio"
APP_HOST = os.getenv("OCR_HOST", "127.0.0.1")
APP_PORT = os.getenv("OCR_PORT", "8095")
APP_URL = f"http://{APP_HOST}:{APP_PORT}"


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


class ControlPanel:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root_dir = project_root()
        self.service_exe = self.root_dir / "LocalOCRStudioService.exe"
        self.log_path = self.root_dir / "logs" / "service.log"
        self.tray = None
        self.last_log_size = -1

        self.service_status = tk.StringVar(value="Checking…")
        self.web_status = tk.StringVar(value="Checking…")
        self.startup_var = tk.BooleanVar(value=self.startup_shortcut().exists())
        self.minimize_var = tk.BooleanVar(value=True)

        self.root.title("Local OCR Studio Control Panel")
        self.root.geometry("760x560")
        self.root.minsize(680, 480)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._build_ui()
        self._create_tray()
        self.refresh()
        self.root.after(2500, self.periodic_refresh)
        self.root.after(1500, self.refresh_logs)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(outer)
        header.pack(fill=tk.X)
        ttk.Label(
            header,
            text="Local OCR Studio",
            font=("Segoe UI", 18, "bold"),
        ).pack(side=tk.LEFT)
        ttk.Label(
            header,
            textvariable=self.service_status,
            font=("Segoe UI", 11, "bold"),
        ).pack(side=tk.RIGHT)

        status = ttk.LabelFrame(outer, text="Status", padding=12)
        status.pack(fill=tk.X, pady=(14, 10))
        ttk.Label(status, text=f"Web interface: {APP_URL}").grid(row=0, column=0, sticky="w")
        ttk.Label(status, textvariable=self.web_status).grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(status, text=f"Project: {self.root_dir}").grid(row=2, column=0, sticky="w", pady=(4, 0))

        controls = ttk.LabelFrame(outer, text="Service controls", padding=12)
        controls.pack(fill=tk.X)
        for index, (label, command) in enumerate([
            ("Start", self.start_service),
            ("Stop", self.stop_service),
            ("Restart", self.restart_service),
            ("Open Web UI", lambda: webbrowser.open(APP_URL)),
            ("Refresh", self.refresh),
        ]):
            ttk.Button(controls, text=label, command=command, width=14).grid(
                row=0, column=index, padx=(0 if index == 0 else 6, 0)
            )

        service_setup = ttk.LabelFrame(outer, text="Windows integration", padding=12)
        service_setup.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(
            service_setup,
            text="Install / Repair Service",
            command=self.install_service,
        ).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(
            service_setup,
            text="Remove Service",
            command=self.remove_service,
        ).grid(row=0, column=1, padx=(0, 8))
        ttk.Checkbutton(
            service_setup,
            text="Start control panel when I sign in",
            variable=self.startup_var,
            command=self.toggle_startup,
        ).grid(row=0, column=2, sticky="w")
        ttk.Checkbutton(
            service_setup,
            text="Close button minimizes to tray",
            variable=self.minimize_var,
        ).grid(row=1, column=2, sticky="w", pady=(7, 0))

        log_frame = ttk.LabelFrame(outer, text="Service log", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Consolas", 9),
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        footer = ttk.Frame(outer)
        footer.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(footer, text="Open Log Folder", command=self.open_log_folder).pack(side=tk.LEFT)
        ttk.Button(footer, text="Exit Control Panel", command=self.exit_app).pack(side=tk.RIGHT)

    def run_sc(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["sc.exe", *args],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

    def query_service(self) -> str:
        result = self.run_sc("query", SERVICE_NAME)
        output = (result.stdout + result.stderr).upper()
        if "FAILED 1060" in output or "DOES NOT EXIST" in output:
            return "Not installed"
        if "RUNNING" in output:
            return "Running"
        if "START_PENDING" in output:
            return "Starting"
        if "STOP_PENDING" in output:
            return "Stopping"
        if "STOPPED" in output:
            return "Stopped"
        return "Unknown"

    def check_web(self) -> bool:
        try:
            with urllib.request.urlopen(f"{APP_URL}/api/status", timeout=1.5) as response:
                return response.status == 200
        except Exception:
            return False

    def refresh(self) -> None:
        def worker() -> None:
            service = self.query_service()
            web = self.check_web()
            self.root.after(0, lambda: self.service_status.set(service))
            self.root.after(
                0,
                lambda: self.web_status.set(
                    "Web application is responding" if web else "Web application is not responding"
                ),
            )
            self._update_tray_title(service)
        threading.Thread(target=worker, daemon=True).start()

    def periodic_refresh(self) -> None:
        self.refresh()
        self.root.after(4000, self.periodic_refresh)

    def service_action(self, action: str) -> None:
        def worker() -> None:
            result = self.run_sc(action, SERVICE_NAME)
            if result.returncode != 0:
                error = (result.stderr or result.stdout).strip()
                self.root.after(0, lambda: messagebox.showerror("Service error", error))
            self.root.after(700, self.refresh)
        threading.Thread(target=worker, daemon=True).start()

    def start_service(self) -> None:
        self.service_action("start")

    def stop_service(self) -> None:
        self.service_action("stop")

    def restart_service(self) -> None:
        def worker() -> None:
            self.run_sc("stop", SERVICE_NAME)
            import time
            for _ in range(20):
                if self.query_service() in {"Stopped", "Not installed"}:
                    break
                time.sleep(0.5)
            self.run_sc("start", SERVICE_NAME)
            self.root.after(700, self.refresh)
        threading.Thread(target=worker, daemon=True).start()

    def elevated_powershell(self, script: str) -> None:
        code = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            "powershell.exe",
            f'-NoProfile -ExecutionPolicy Bypass -Command "{script}"',
            str(self.root_dir),
            1,
        )
        if code <= 32:
            messagebox.showerror(
                "Administrator permission",
                "The elevated command could not be started.",
            )
        else:
            self.root.after(1800, self.refresh)

    def install_service(self) -> None:
        if not self.service_exe.exists():
            messagebox.showerror(
                "Missing service executable",
                f"Service executable was not found:\n{self.service_exe}\n\nRun build_windows_executables.ps1 first.",
            )
            return
        exe = str(self.service_exe).replace("'", "''")
        self.elevated_powershell(
            f"& '{exe}' --startup auto install; & '{exe}' start"
        )

    def remove_service(self) -> None:
        if not messagebox.askyesno(
            "Remove service",
            "Stop and remove the Local OCR Studio Windows service?",
        ):
            return
        if self.service_exe.exists():
            exe = str(self.service_exe).replace("'", "''")
            self.elevated_powershell(
                f"& '{exe}' stop; Start-Sleep -Seconds 1; & '{exe}' remove"
            )
        else:
            self.elevated_powershell(
                "sc.exe stop LocalOCRStudio; Start-Sleep -Seconds 1; "
                "sc.exe delete LocalOCRStudio"
            )

    def startup_shortcut(self) -> Path:
        startup = Path(os.getenv("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        return startup / "Local OCR Studio Control Panel.lnk"

    def toggle_startup(self) -> None:
        shortcut = self.startup_shortcut()
        if self.startup_var.get():
            if not getattr(sys, "frozen", False):
                messagebox.showwarning("Executable required", "Build and run the executable before enabling startup.")
                self.startup_var.set(False)
                return
            shortcut.parent.mkdir(parents=True, exist_ok=True)
            target = str(Path(sys.executable).resolve()).replace("'", "''")
            working = str(self.root_dir).replace("'", "''")
            output = str(shortcut).replace("'", "''")
            command = (
                "$w=New-Object -ComObject WScript.Shell;"
                f"$s=$w.CreateShortcut('{output}');"
                f"$s.TargetPath='{target}';"
                f"$s.WorkingDirectory='{working}';"
                "$s.Arguments='--tray';$s.Save()"
            )
            subprocess.run(["powershell.exe", "-NoProfile", "-Command", command], check=True)
        else:
            shortcut.unlink(missing_ok=True)

    def refresh_logs(self) -> None:
        try:
            if self.log_path.exists():
                size = self.log_path.stat().st_size
                if size != self.last_log_size:
                    content = self.log_path.read_text(encoding="utf-8", errors="replace")
                    content = content[-50000:]
                    self.log_text.configure(state=tk.NORMAL)
                    self.log_text.delete("1.0", tk.END)
                    self.log_text.insert(tk.END, content)
                    self.log_text.see(tk.END)
                    self.log_text.configure(state=tk.DISABLED)
                    self.last_log_size = size
        finally:
            self.root.after(2000, self.refresh_logs)

    def open_log_folder(self) -> None:
        folder = self.root_dir / "logs"
        folder.mkdir(exist_ok=True)
        os.startfile(folder)

    def _tray_image(self) -> Image.Image:
        image = Image.new("RGB", (64, 64), "#18233a")
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((7, 7, 57, 57), radius=12, fill="#2f80ed")
        draw.text((18, 15), "OCR", fill="white")
        return image

    def _create_tray(self) -> None:
        if pystray is None:
            return
        menu = pystray.Menu(
            pystray.MenuItem("Open Control Panel", self.show_window, default=True),
            pystray.MenuItem("Open Web UI", lambda: webbrowser.open(APP_URL)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Start Service", lambda: self.start_service()),
            pystray.MenuItem("Stop Service", lambda: self.stop_service()),
            pystray.MenuItem("Restart Service", lambda: self.restart_service()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit Control Panel", lambda: self.root.after(0, self.exit_app)),
        )
        self.tray = pystray.Icon("LocalOCRStudio", self._tray_image(), "Local OCR Studio", menu)
        threading.Thread(target=self.tray.run, daemon=True).start()

    def _update_tray_title(self, status: str) -> None:
        if self.tray:
            self.tray.title = f"Local OCR Studio — {status}"

    def show_window(self, *_args) -> None:
        self.root.after(0, self._show_window)

    def _show_window(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def on_close(self) -> None:
        if self.minimize_var.get() and self.tray is not None:
            self.root.withdraw()
        else:
            self.exit_app()

    def exit_app(self) -> None:
        if self.tray:
            self.tray.stop()
            self.tray = None
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    panel = ControlPanel(root)
    if "--tray" in sys.argv:
        root.after(300, root.withdraw)
    root.mainloop()


if __name__ == "__main__":
    main()
