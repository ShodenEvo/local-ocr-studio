
from __future__ import annotations

import os
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

APP_HOST = "127.0.0.1"
APP_PORT = 8095
APP_URL = f"http://{APP_HOST}:{APP_PORT}"
CUDA_INDEX_URL = "https://download.pytorch.org/whl/cu130"

REQUIRED_IMPORTS = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn[standard]",
    "jinja2": "jinja2",
    "multipart": "python-multipart",
    "cv2": "opencv-python",
    "numpy": "numpy",
    "PIL": "pillow",
    "pytesseract": "pytesseract",
    "easyocr": "easyocr",
}

BASE_PACKAGES = [
    "fastapi",
    "uvicorn[standard]",
    "jinja2",
    "python-multipart",
    "opencv-python",
    "numpy",
    "pillow",
    "pytesseract",
    "easyocr",
]


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


class OCRStudioManager:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root_dir = project_root()
        self.process: subprocess.Popen[str] | None = None
        self.worker: threading.Thread | None = None
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.stop_reader = threading.Event()

        self.status_var = tk.StringVar(value="Stopped")
        self.install_status_var = tk.StringVar(value="Not checked")
        self.gpu_var = tk.StringVar(value="GPU status not checked")
        self.pid_var = tk.StringVar(value="PID: —")
        self.progress_var = tk.DoubleVar(value=0)

        self.use_cuda_var = tk.BooleanVar(value=True)
        self.install_requirements_var = tk.BooleanVar(value=True)
        self.create_shortcut_var = tk.BooleanVar(value=True)
        self.open_after_start_var = tk.BooleanVar(value=True)

        self.root.title("Local OCR Studio Manager")
        self.root.geometry("860x650")
        self.root.minsize(760, 560)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.build_ui()
        self.root.after(100, self.drain_log_queue)
        self.refresh_status()
        self.check_environment_async()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(outer)
        header.pack(fill=tk.X)

        ttk.Label(
            header,
            text="Local OCR Studio Manager",
            font=("Segoe UI", 18, "bold"),
        ).pack(side=tk.LEFT)

        ttk.Label(
            header,
            textvariable=self.status_var,
            font=("Segoe UI", 11, "bold"),
        ).pack(side=tk.RIGHT)

        ttk.Label(
            outer,
            text=f"Project: {self.root_dir}",
        ).pack(anchor=tk.W, pady=(8, 0))

        ttk.Label(
            outer,
            textvariable=self.gpu_var,
        ).pack(anchor=tk.W)

        notebook = ttk.Notebook(outer)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        self.control_tab = ttk.Frame(notebook, padding=12)
        self.install_tab = ttk.Frame(notebook, padding=12)
        self.logs_tab = ttk.Frame(notebook, padding=12)

        notebook.add(self.control_tab, text="Control")
        notebook.add(self.install_tab, text="Install / Repair")
        notebook.add(self.logs_tab, text="Logs")

        self.build_control_tab()
        self.build_install_tab()
        self.build_logs_tab()

    def build_control_tab(self) -> None:
        info = ttk.LabelFrame(self.control_tab, text="Server", padding=12)
        info.pack(fill=tk.X)

        ttk.Label(info, text=f"Web interface: {APP_URL}").pack(anchor=tk.W)
        ttk.Label(info, textvariable=self.pid_var).pack(anchor=tk.W)

        ttk.Checkbutton(
            info,
            text="Open browser automatically after startup",
            variable=self.open_after_start_var,
        ).pack(anchor=tk.W, pady=(8, 0))

        buttons = ttk.Frame(self.control_tab)
        buttons.pack(fill=tk.X, pady=14)

        self.start_button = ttk.Button(
            buttons, text="Start", command=self.start_server, width=16
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 6))

        self.stop_button = ttk.Button(
            buttons, text="Stop", command=self.stop_server, width=16
        )
        self.stop_button.pack(side=tk.LEFT, padx=6)

        self.restart_button = ttk.Button(
            buttons, text="Restart", command=self.restart_server, width=16
        )
        self.restart_button.pack(side=tk.LEFT, padx=6)

        ttk.Button(
            buttons,
            text="Open Web UI",
            command=lambda: webbrowser.open(APP_URL),
            width=16,
        ).pack(side=tk.LEFT, padx=6)

        tools = ttk.LabelFrame(self.control_tab, text="Tools", padding=12)
        tools.pack(fill=tk.X)

        ttk.Button(
            tools,
            text="Open Project Folder",
            command=self.open_project_folder,
        ).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(
            tools,
            text="Check Environment",
            command=self.check_environment_async,
        ).pack(side=tk.LEFT, padx=6)

        ttk.Button(
            tools,
            text="Check GPU",
            command=self.check_gpu_async,
        ).pack(side=tk.LEFT, padx=6)

    def build_install_tab(self) -> None:
        ttk.Label(
            self.install_tab,
            text="Install or repair the Python runtime used by Local OCR Studio.",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor=tk.W)

        ttk.Label(
            self.install_tab,
            text=(
                "This installs the virtual environment and Python dependencies. "
                "The application files under app\\ must already exist in this folder."
            ),
            wraplength=760,
        ).pack(anchor=tk.W, pady=(4, 12))

        options = ttk.LabelFrame(self.install_tab, text="Installation options", padding=12)
        options.pack(fill=tk.X)

        ttk.Checkbutton(
            options,
            text="Install/repair application dependencies",
            variable=self.install_requirements_var,
        ).pack(anchor=tk.W)

        ttk.Checkbutton(
            options,
            text="Install NVIDIA CUDA-enabled PyTorch (CUDA 13.0 wheel)",
            variable=self.use_cuda_var,
        ).pack(anchor=tk.W, pady=(5, 0))

        ttk.Checkbutton(
            options,
            text="Create a Desktop shortcut to OCRStudioManager.exe",
            variable=self.create_shortcut_var,
        ).pack(anchor=tk.W, pady=(5, 0))

        actions = ttk.Frame(self.install_tab)
        actions.pack(fill=tk.X, pady=14)

        self.install_button = ttk.Button(
            actions,
            text="Install / Repair",
            command=self.install_async,
            width=20,
        )
        self.install_button.pack(side=tk.LEFT)

        ttk.Button(
            actions,
            text="Verify Installation",
            command=self.check_environment_async,
            width=20,
        ).pack(side=tk.LEFT, padx=8)

        ttk.Button(
            actions,
            text="Open Tesseract Folder",
            command=self.open_tesseract_folder,
            width=20,
        ).pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(
            self.install_tab,
            variable=self.progress_var,
            maximum=100,
        )
        self.progress.pack(fill=tk.X, pady=(4, 8))

        ttk.Label(
            self.install_tab,
            textvariable=self.install_status_var,
            wraplength=760,
        ).pack(anchor=tk.W)

        notes = ttk.LabelFrame(self.install_tab, text="Notes", padding=12)
        notes.pack(fill=tk.X, pady=(16, 0))

        ttk.Label(
            notes,
            text=(
                "• Tesseract itself is a separate Windows program and is not silently installed.\n"
                "• If Tesseract is missing, install it under C:\\Program Files\\Tesseract-OCR.\n"
                "• CUDA acceleration is used by EasyOCR/PyTorch. Tesseract remains CPU-based.\n"
                "• The installer can be run repeatedly to repair the environment."
            ),
            justify=tk.LEFT,
        ).pack(anchor=tk.W)

    def build_logs_tab(self) -> None:
        self.log_text = scrolledtext.ScrolledText(
            self.logs_tab,
            wrap=tk.WORD,
            font=("Consolas", 10),
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        footer = ttk.Frame(self.logs_tab)
        footer.pack(fill=tk.X, pady=(8, 0))

        ttk.Button(
            footer,
            text="Clear Log",
            command=self.clear_log,
        ).pack(side=tk.LEFT)

        ttk.Button(
            footer,
            text="Save Log",
            command=self.save_log,
        ).pack(side=tk.LEFT, padx=6)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log(self, message: str) -> None:
        self.log_queue.put(message)

    def drain_log_queue(self) -> None:
        while True:
            try:
                message = self.log_queue.get_nowait()
            except queue.Empty:
                break

            timestamp = time.strftime("%H:%M:%S")
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)
            self.log_text.configure(state=tk.DISABLED)

        self.root.after(100, self.drain_log_queue)

    def clear_log(self) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def save_log(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save log",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        content = self.log_text.get("1.0", tk.END)
        Path(path).write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------
    # Paths and checks
    # ------------------------------------------------------------------

    @property
    def venv_python(self) -> Path:
        return self.root_dir / "venv" / "Scripts" / "python.exe"

    def find_system_python(self) -> list[str] | None:
        candidates = [
            ["py", "-3"],
            ["python"],
        ]
        for command in candidates:
            try:
                result = subprocess.run(
                    command + ["--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    return command
            except Exception:
                continue
        return None

    def app_files_exist(self) -> bool:
        return (self.root_dir / "app" / "main.py").exists()

    # ------------------------------------------------------------------
    # Installation
    # ------------------------------------------------------------------

    def install_async(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Busy", "Another operation is already running.")
            return

        self.worker = threading.Thread(target=self.install_environment, daemon=True)
        self.worker.start()

    def install_environment(self) -> None:
        self.root.after(0, lambda: self.install_button.configure(state=tk.DISABLED))
        self.set_install_progress(2, "Starting installation...")

        try:
            if not self.app_files_exist():
                raise FileNotFoundError(
                    f"Application entry point not found:\n"
                    f"{self.root_dir / 'app' / 'main.py'}"
                )

            if not self.venv_python.exists():
                python_cmd = self.find_system_python()
                if not python_cmd:
                    raise RuntimeError(
                        "Python 3 was not found. Install Python 3.11 or newer "
                        "and enable 'Add Python to PATH'."
                    )

                self.set_install_progress(8, "Creating virtual environment...")
                self.run_command(
                    python_cmd + ["-m", "venv", str(self.root_dir / "venv")]
                )

            self.set_install_progress(18, "Updating pip...")
            self.run_command(
                [str(self.venv_python), "-m", "pip", "install", "--upgrade", "pip"]
            )

            if self.install_requirements_var.get():
                self.set_install_progress(28, "Installing application dependencies...")
                requirements = self.root_dir / "requirements.txt"

                if requirements.exists():
                    self.run_command(
                        [
                            str(self.venv_python),
                            "-m",
                            "pip",
                            "install",
                            "-r",
                            str(requirements),
                        ]
                    )
                else:
                    self.run_command(
                        [str(self.venv_python), "-m", "pip", "install", *BASE_PACKAGES]
                    )

            if self.use_cuda_var.get():
                self.set_install_progress(58, "Installing CUDA-enabled PyTorch...")
                self.run_command(
                    [
                        str(self.venv_python),
                        "-m",
                        "pip",
                        "uninstall",
                        "-y",
                        "torch",
                        "torchvision",
                        "torchaudio",
                    ],
                    allow_failure=True,
                )
                self.run_command(
                    [
                        str(self.venv_python),
                        "-m",
                        "pip",
                        "install",
                        "torch",
                        "torchvision",
                        "--index-url",
                        CUDA_INDEX_URL,
                    ]
                )
                # EasyOCR may have been installed before torch replacement.
                self.run_command(
                    [
                        str(self.venv_python),
                        "-m",
                        "pip",
                        "install",
                        "--upgrade",
                        "easyocr",
                    ]
                )

            self.set_install_progress(82, "Verifying Python modules...")
            check = self.environment_report()
            self.log(check)

            if self.create_shortcut_var.get():
                self.set_install_progress(92, "Creating Desktop shortcut...")
                self.create_desktop_shortcut()

            self.set_install_progress(100, "Installation completed successfully.")
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Installation Complete",
                    "Local OCR Studio runtime has been installed or repaired.",
                ),
            )
            self.check_gpu_async()

        except Exception as exc:
            self.log(f"INSTALLATION ERROR: {exc}")
            self.set_install_progress(0, f"Installation failed: {exc}")
            self.root.after(
                0,
                lambda error=str(exc): messagebox.showerror(
                    "Installation Failed", error
                ),
            )
        finally:
            self.root.after(0, lambda: self.install_button.configure(state=tk.NORMAL))

    def run_command(
        self,
        command: list[str],
        *,
        allow_failure: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        printable = subprocess.list2cmdline(command)
        self.log(f"> {printable}")

        process = subprocess.Popen(
            command,
            cwd=self.root_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        assert process.stdout is not None
        for line in process.stdout:
            self.log(line.rstrip())

        return_code = process.wait()

        if return_code != 0 and not allow_failure:
            raise RuntimeError(
                f"Command failed with exit code {return_code}:\n{printable}"
            )

        return subprocess.CompletedProcess(command, return_code)

    def set_install_progress(self, value: float, message: str) -> None:
        self.log(message)
        self.root.after(0, lambda: self.progress_var.set(value))
        self.root.after(0, lambda: self.install_status_var.set(message))

    def create_desktop_shortcut(self) -> None:
        if not getattr(sys, "frozen", False):
            self.log(
                "Desktop shortcut skipped because the manager is running as a Python script."
            )
            return

        exe_path = Path(sys.executable).resolve()
        desktop = Path.home() / "Desktop"
        shortcut = desktop / "Local OCR Studio.lnk"

        escaped_target = str(exe_path).replace("'", "''")
        escaped_workdir = str(self.root_dir).replace("'", "''")
        escaped_shortcut = str(shortcut).replace("'", "''")

        ps_script = (
            "$ws=New-Object -ComObject WScript.Shell;"
            f"$s=$ws.CreateShortcut('{escaped_shortcut}');"
            f"$s.TargetPath='{escaped_target}';"
            f"$s.WorkingDirectory='{escaped_workdir}';"
            "$s.Description='Local OCR Studio Manager';"
            "$s.Save();"
        )

        subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_script],
            check=True,
        )
        self.log(f"Desktop shortcut created: {shortcut}")

    # ------------------------------------------------------------------
    # Environment reporting
    # ------------------------------------------------------------------

    def check_environment_async(self) -> None:
        threading.Thread(target=self.check_environment, daemon=True).start()

    def check_environment(self) -> None:
        try:
            report = self.environment_report()
            self.log(report)
            summary = report.splitlines()[0] if report else "Environment checked."
            self.root.after(0, lambda: self.install_status_var.set(summary))
        except Exception as exc:
            self.log(f"Environment check failed: {exc}")
            self.root.after(
                0,
                lambda: self.install_status_var.set(f"Environment check failed: {exc}"),
            )

    def environment_report(self) -> str:
        if not self.venv_python.exists():
            return "Virtual environment: missing"

        script = r