import asyncio
import sys
import os
import ctypes
import re
import signal
import subprocess
from typing import Callable, Optional

# Constants for State
STATE_STOPPED = "Stopped"
STATE_STARTING = "Starting"
STATE_TUNNEL_A_RUNNING = "Tunnel A Running"
STATE_CONNECTED = "Connected (RSD Found)"
STATE_SIMULATING = "Simulating..."
STATE_ERROR = "Error"

class ProcessManager:
    def __init__(self, log_callback: Callable[[str], None], status_callback: Callable[[str], None]):
        self.log_callback = log_callback
        self.status_callback = status_callback

        self.proc_tunnel_a: Optional[asyncio.subprocess.Process] = None
        self.proc_tunnel_b: Optional[asyncio.subprocess.Process] = None
        self.proc_sim: Optional[asyncio.subprocess.Process] = None

        self.rsd_ip: Optional[str] = None
        self.rsd_port: Optional[str] = None

        self.state = STATE_STOPPED
        self.is_mock = False

        # Determine execution mode
        if sys.platform != 'win32' or os.environ.get('IGEOFAKE_MOCK') == '1':
            self.is_mock = True
            self.log("INFO: Running in MOCK MODE")

    def log(self, message: str):
        self.log_callback(message)

    def set_state(self, new_state: str):
        self.state = new_state
        self.status_callback(new_state)

    def check_admin(self) -> bool:
        if self.is_mock:
            return True
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    async def _read_stream(self, stream, process_name, rsd_parser=False):
        """Reads stdout/stderr from a subprocess and logs it."""
        while True:
            line_bytes = await stream.readline()
            if not line_bytes:
                break
            line = line_bytes.decode('utf-8', errors='replace').strip()
            if line:
                self.log(f"[{process_name}] {line}")

                if rsd_parser:
                    # Regex: Use the follow connection option: --rsd ([a-f0-9:]+) (\d+)
                    match = re.search(r'--rsd\s+([a-f0-9:]+)\s+(\d+)', line)
                    if match:
                        new_ip = match.group(1)
                        new_port = match.group(2)
                        
                        if new_ip != self.rsd_ip or new_port != self.rsd_port:
                            self.rsd_ip = new_ip
                            self.rsd_port = new_port
                            self.log(f"SUCCESS: RSD Updated - IP: {self.rsd_ip}, Port: {self.rsd_port}")
                            if self.state != STATE_SIMULATING:
                                self.set_state(STATE_CONNECTED)

    async def _wait_for_exit(self, proc, name):
        """Waits for process exit and handles errors."""
        await proc.wait()

        # Check if this process is still the active one
        is_active = False
        if name == "Tunnel A" and self.proc_tunnel_a == proc:
            is_active = True
        elif name == "Tunnel B" and self.proc_tunnel_b == proc:
            is_active = True
        elif name == "Simulate" and self.proc_sim == proc:
            is_active = True

        # If not active (replaced or set to None), we assume it was intentionally killed
        if not is_active:
            return

        if proc.returncode != 0 and proc.returncode is not None:
             if self.state not in [STATE_STOPPED, STATE_ERROR]:
                 self.log(f"ERROR: {name} exited unexpectedly with code {proc.returncode}")
                 self.set_state(STATE_ERROR)

    async def start_tunnel_a(self):
        if self.state != STATE_STOPPED and self.state != STATE_ERROR:
            self.log("Services already running or starting.")
            return

        self.set_state(STATE_STARTING)
        self.rsd_ip = None
        self.rsd_port = None

        try:
            # 1. Start Tunnel A
            cmd_a = self._get_command("tunnel_a")
            self.log(f"Starting Tunnel A: {' '.join(cmd_a)}")
            
            # Force unbuffered output
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"

            self.proc_tunnel_a = await asyncio.create_subprocess_exec(
                *cmd_a,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env
            )
            asyncio.create_task(self._read_stream(self.proc_tunnel_a.stdout, "Tunnel A"))
            asyncio.create_task(self._wait_for_exit(self.proc_tunnel_a, "Tunnel A"))
            
            self.set_state(STATE_TUNNEL_A_RUNNING)

        except Exception as e:
            self.log(f"CRITICAL ERROR starting Tunnel A: {e}")
            self.set_state(STATE_ERROR)
            await self.stop_services()

    async def start_tunnel_b(self):
        if self.state != STATE_TUNNEL_A_RUNNING:
            self.log("Tunnel A must be running before starting Tunnel B.")
            return

        self.set_state(STATE_STARTING)

        try:
            # 2. Start Tunnel B
            cmd_b = self._get_command("tunnel_b")
            self.log(f"Starting Tunnel B: {' '.join(cmd_b)}")
            
            # Force unbuffered output
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"

            self.proc_tunnel_b = await asyncio.create_subprocess_exec(
                *cmd_b,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env
            )
            asyncio.create_task(self._read_stream(self.proc_tunnel_b.stdout, "Tunnel B", rsd_parser=True))
            asyncio.create_task(self._wait_for_exit(self.proc_tunnel_b, "Tunnel B"))

        except Exception as e:
            self.log(f"CRITICAL ERROR starting Tunnel B: {e}")
            self.set_state(STATE_ERROR)
            await self.stop_services()

    async def set_location(self, lat: str, lon: str):
        if not self.rsd_ip or not self.rsd_port:
            self.log("ERROR: RSD Connection info not found yet.")
            return

        # Check and kill existing Sim process
        if self.proc_sim:
            old_proc = self.proc_sim
            self.proc_sim = None # Detach first so _wait_for_exit ignores it
            self.log("Stopping previous simulation process...")
            await self._kill_process(old_proc)

        try:
            cmd_c = self._get_command("set_location", self.rsd_ip, self.rsd_port, lat, lon)
            self.log(f"Setting Location: {' '.join(cmd_c)}")

            self.proc_sim = await asyncio.create_subprocess_exec(
                *cmd_c,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            asyncio.create_task(self._read_stream(self.proc_sim.stdout, "Simulate"))
            asyncio.create_task(self._wait_for_exit(self.proc_sim, "Simulate"))

            self.set_state(STATE_SIMULATING)

        except Exception as e:
            self.log(f"ERROR setting location: {e}")

    async def play_route(self, gpx_path: str, noise: str):
        if not self.rsd_ip or not self.rsd_port:
            self.log("ERROR: RSD Connection info not found yet.")
            return

        # Check and kill existing Sim process
        if self.proc_sim:
            old_proc = self.proc_sim
            self.proc_sim = None # Detach first so _wait_for_exit ignores it
            self.log("Stopping previous simulation process...")
            await self._kill_process(old_proc)

        try:
            cmd_play = self._get_command("play", self.rsd_ip, self.rsd_port, gpx_path, noise)
            self.log(f"Playing Route: {' '.join(cmd_play)}")

            self.proc_sim = await asyncio.create_subprocess_exec(
                *cmd_play,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            asyncio.create_task(self._read_stream(self.proc_sim.stdout, "Simulate"))
            asyncio.create_task(self._wait_for_exit(self.proc_sim, "Simulate"))

            self.set_state(STATE_SIMULATING)

        except Exception as e:
            self.log(f"ERROR playing route: {e}")

    async def clear_location(self):
        # Kill existing simulation first
        if self.proc_sim:
            old_proc = self.proc_sim
            self.proc_sim = None
            await self._kill_process(old_proc)

        if self.state == STATE_SIMULATING:
             self.set_state(STATE_CONNECTED)

        try:
            cmd_d = self._get_command("clear_location")
            self.log(f"Clearing Location: {' '.join(cmd_d)}")

            proc = await asyncio.create_subprocess_exec(
                *cmd_d,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            await proc.communicate()
            self.log("Location cleared.")

        except Exception as e:
            self.log(f"ERROR clearing location: {e}")

    async def stop_services(self):
        self.log("Stopping all services...")

        tasks = []
        if self.proc_sim:
            tasks.append(self._kill_process(self.proc_sim))
        if self.proc_tunnel_b:
            tasks.append(self._kill_process(self.proc_tunnel_b))
        if self.proc_tunnel_a:
            tasks.append(self._kill_process(self.proc_tunnel_a))

        # Detach references immediately so _wait_for_exit doesn't trigger Error state
        self.proc_sim = None
        self.proc_tunnel_b = None
        self.proc_tunnel_a = None
        self.rsd_ip = None
        self.rsd_port = None

        if tasks:
            await asyncio.gather(*tasks)

        self.set_state(STATE_STOPPED)
        self.log("All services stopped.")

    async def _kill_process(self, proc: asyncio.subprocess.Process):
        if proc.returncode is not None:
            return

        pid = proc.pid
        self.log(f"Killing process {pid}...")

        try:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                self.log(f"Process {pid} did not terminate, forcing kill...")
                if self.is_mock:
                     proc.kill()
                else:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
        except ProcessLookupError:
            pass
        except Exception as e:
            self.log(f"Error killing process {pid}: {e}")

    def _get_command(self, cmd_type: str, *args) -> list[str]:
        if self.is_mock:
            base = [sys.executable, "mock_cli.py"]
            if cmd_type == "tunnel_a":
                return base + ["tunnel_a"]
            elif cmd_type == "tunnel_b":
                return base + ["tunnel_b"]
            elif cmd_type == "set_location":
                return base + ["set_location", "--", args[2], args[3]]
            elif cmd_type == "play":
                 return base + ["play", "--", args[2], args[3]]
            elif cmd_type == "clear_location":
                return base + ["clear_location"]
        else:
            # Determine the executable path
            if getattr(sys, 'frozen', False):
                # Running in PyInstaller bundle
                # Executable is in the same directory as the main executable
                base_path = os.path.dirname(sys.executable)
                pmd3_exe = os.path.join(base_path, "pymobiledevice3")
                if sys.platform == "win32":
                    pmd3_exe += ".exe"
            else:
                # Running from source, rely on PATH or venv
                pmd3_exe = "pymobiledevice3"

            if cmd_type == "tunnel_a":
                return [pmd3_exe, "remote", "tunneld"]
            elif cmd_type == "tunnel_b":
                return [pmd3_exe, "lockdown", "start-tunnel"]
            elif cmd_type == "set_location":
                rsd_ip, rsd_port, lat, lon = args
                return [
                    pmd3_exe, "developer", "dvt", "simulate-location", "set",
                    "--rsd", rsd_ip, rsd_port,
                    "--", lat, lon
                ]
            elif cmd_type == "play":
                rsd_ip, rsd_port, gpx_path, noise = args
                return [
                    pmd3_exe, "developer", "dvt", "simulate-location", "play",
                    "--rsd", rsd_ip, rsd_port,
                    "--", gpx_path, noise
                ]
            elif cmd_type == "clear_location":
                return [pmd3_exe, "developer", "dvt", "simulate-location", "clear"]
        return []
