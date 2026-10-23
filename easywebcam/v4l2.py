"""
EasyWebcam - V4L2 Loopback Dynamic Lifecycle Manager
Creates the virtual webcam device on startup and removes it cleanly on shutdown.
Enforces fixed, standard resolution and stride to prevent horizontal banding/artifacts.
"""

import os
import subprocess
import time
from typing import Optional

class V4L2DeviceManager:
    def __init__(self, device: Optional[str] = None, card_label: str = "EasyWebcam", width: int = 1920, height: int = 1080):
        self.device = device or "/dev/video0"
        self.card_label = card_label
        self.target_width = width
        self.target_height = height
        self.pixel_format = "YUYV"
        self._fd: Optional[int] = None
        self._keep_device = False

    def is_module_loaded(self) -> bool:
        """Checks if v4l2loopback kernel module is currently loaded."""
        return os.path.exists("/sys/module/v4l2loopback")

    def start(self) -> bool:
        """
        Dynamically loads the kernel module and creates the virtual webcam device.
        """
        if not self.is_module_loaded():
            print(f"[*] Dynamically creating virtual webcam ({self.card_label})...")
            try:
                subprocess.run(
                    [
                        "sudo", "modprobe", "v4l2loopback",
                        "exclusive_caps=1",
                        f"card_label={self.card_label}",
                        "max_buffers=2"
                    ],
                    check=True,
                    capture_output=True
                )
                for _ in range(20):
                    if os.path.exists(self.device):
                        break
                    time.sleep(0.05)
            except Exception as e:
                print(f"[!] Error loading v4l2loopback: {e}")
                return False
        else:
            print(f"[*] Virtual webcam module active on {self.device}...")

        if not os.path.exists(self.device):
            import glob
            devs = glob.glob("/dev/video*")
            if devs:
                self.device = devs[0]
            else:
                print(f"[!] Failed to find created video device.")
                return False

        try:
            subprocess.run(["sudo", "chmod", "666", self.device], check=False, capture_output=True)
        except Exception:
            pass

        # Pre-configure fixed standard resolution before any app (Discord, OBS) connects
        self.setup_format(self.target_width, self.target_height, self.pixel_format)

        print(f"[✓] Virtual webcam online: {self.device} ({self.card_label}) [{self.target_width}x{self.target_height}]")
        return True

    def setup_format(self, width: int, height: int, pixel_format: str = "YUYV") -> bool:
        """Sets resolution and pixel format via v4l2-ctl and opens device descriptor."""
        if self._fd is not None:
            try:
                os.close(self._fd)
            except Exception:
                pass
            self._fd = None

        self.target_width = width
        self.target_height = height
        self.pixel_format = pixel_format

        cmd = [
            "v4l2-ctl",
            "-d", self.device,
            f"--set-fmt-video-out=width={width},height={height},pixelformat={pixel_format}"
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True)
        except Exception as e:
            print(f"[!] Warning setting format: {e}")

        try:
            # Non-blocking write descriptor to prevent event-loop stalls
            self._fd = os.open(self.device, os.O_WRONLY)
            return True
        except Exception as e:
            print(f"[!] Error opening {self.device}: {e}")
            return False

    def write_frame(self, raw_bytes: bytes) -> bool:
        """Writes raw frame bytes directly into the virtual webcam."""
        if self._fd is None:
            return False
        try:
            os.write(self._fd, raw_bytes)
            return True
        except Exception:
            return False

    def stop(self):
        """
        Closes descriptor and unloads the kernel module, completely removing
        the virtual webcam from the operating system.
        """
        if self._fd is not None:
            try:
                os.close(self._fd)
            except Exception:
                pass
            self._fd = None

        if self._keep_device:
            return

        print(f"\n[*] Cleaning up: Removing {self.device} from system...")
        time.sleep(0.2)
        res = subprocess.run(["sudo", "modprobe", "-r", "v4l2loopback"], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[✓] Virtual webcam device removed. System clean.")
        else:
            # Check if an external application is locking the device
            fuser_res = subprocess.run(["fuser", self.device], capture_output=True, text=True).stdout.strip()
            if fuser_res:
                print(f"[!] Notice: {self.device} is currently kept open by PID {fuser_res} (e.g. Discord camera preview).")
                print(f"    Once you close the camera preview in that app, the device will be released.")
            else:
                # Retry once
                time.sleep(0.5)
                retry_res = subprocess.run(["sudo", "modprobe", "-r", "v4l2loopback"], capture_output=True, text=True)
                if retry_res.returncode == 0:
                    print(f"[✓] Virtual webcam device removed. System clean.")
                else:
                    print(f"[!] Info: {retry_res.stderr.strip()}")
