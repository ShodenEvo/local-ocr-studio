from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import servicemanager
import win32event
import win32service
import win32serviceutil

SERVICE_NAME = "LocalOCRStudio"
SERVICE_DISPLAY_NAME = "Local OCR Studio"
SERVICE_DESCRIPTION = "Runs the Local OCR Studio web application in the background."


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent

        # The service is distributed under:
        #   <project>\service\LocalOCRStudioService.exe
        #
        # Prefer the executable directory only when it contains the project.
        # Otherwise, step up one directory and validate the expected layout.
        candidates = [
            executable_dir,
            executable_dir.parent,
        ]

        for candidate in candidates:
            if (
                (candidate / "app" / "main.py").exists()
                and (candidate / "venv" / "Scripts" / "python.exe").exists()
            ):
                return candidate

        # Keep a deterministic fallback so any raised error includes the
        # expected project-level path rather than service\venv.
        return executable_dir.parent

    return Path(__file__).resolve().parents[1]


class LocalOCRStudioService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY_NAME
    _svc_description_ = SERVICE_DESCRIPTION

    def __init__(self, args: list[str]) -> None:
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.process: subprocess.Popen[str] | None = None
        self.root = project_root()
        self.log_handle = None

    def SvcStop(self) -> None:
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self._stop_process()

    def SvcShutdown(self) -> None:
        self.SvcStop()

    def SvcDoRun(self) -> None:
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
        servicemanager.LogInfoMsg(
            f"{SERVICE_DISPLAY_NAME} service process entered SvcDoRun"
        )
        try:
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            self._run_server()
        except Exception as exc:
            servicemanager.LogErrorMsg(f"{SERVICE_DISPLAY_NAME} failed: {exc}")
            raise
        finally:
            self._stop_process()
            if self.log_handle:
                self.log_handle.close()
                self.log_handle = None
            servicemanager.LogInfoMsg(f"{SERVICE_DISPLAY_NAME} service stopped")

    def _run_server(self) -> None:
        python = self.root / "venv" / "Scripts" / "python.exe"
        app_entry = self.root / "app" / "main.py"
        logs_dir = self.root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        if not python.exists():
            raise FileNotFoundError(f"Virtual environment Python not found: {python}")
        if not app_entry.exists():
            raise FileNotFoundError(f"Application entry point not found: {app_entry}")

        host = os.getenv("OCR_HOST", "127.0.0.1")
        port = os.getenv("OCR_PORT", "8095")
        log_path = logs_dir / "service.log"
        self.log_handle = log_path.open("a", encoding="utf-8", buffering=1)

        creationflags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        # Windows services normally inherit a legacy console encoding.
        # EasyOCR's download progress bar contains Unicode block characters,
        # so force the child Python runtime and redirected output to UTF-8.
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        # Keep EasyOCR models in the application directory. LocalSystem has a
        # different user profile and would otherwise use the system profile.
        easyocr_model_dir = self.root / "models" / "easyocr"
        easyocr_model_dir.mkdir(parents=True, exist_ok=True)
        env["EASYOCR_MODULE_PATH"] = str(easyocr_model_dir)
        env["MODULE_PATH"] = str(easyocr_model_dir)

        command = [
            str(python),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            host,
            "--port",
            str(port),
        ]

        self.log_handle.write(
            f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting: "
            + subprocess.list2cmdline(command)
            + "\n"
        )

        self.process = subprocess.Popen(
            command,
            cwd=self.root,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=self.log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=creationflags,
        )

        while True:
            wait_result = win32event.WaitForSingleObject(self.stop_event, 1000)
            if wait_result == win32event.WAIT_OBJECT_0:
                break

            exit_code = self.process.poll()
            if exit_code is not None:
                raise RuntimeError(f"OCR server exited unexpectedly with code {exit_code}")

    def _stop_process(self) -> None:
        process = self.process
        if process is None or process.poll() is not None:
            return

        try:
            process.send_signal(signal.CTRL_BREAK_EVENT)
            process.wait(timeout=10)
        except Exception:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception:
                process.kill()
        finally:
            self.process = None


def run_service_entrypoint() -> None:
    """Run either as an SCM-hosted service or as a command-line utility."""
    if len(sys.argv) == 1:
        # When the Windows Service Control Manager launches a frozen
        # executable, no command-line action such as "start" or "install"
        # is supplied. Register the service class with pywin32 and enter
        # the SCM dispatcher directly.
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(LocalOCRStudioService)
        servicemanager.StartServiceCtrlDispatcher()
        return

    win32serviceutil.HandleCommandLine(LocalOCRStudioService)


if __name__ == "__main__":
    run_service_entrypoint()

