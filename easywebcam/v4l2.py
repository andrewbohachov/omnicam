"""
EasyWebcam - V4L2 Loopback Dynamic Lifecycle Manager
Creates the virtual webcam device on startup and removes it cleanly on shutdown.
"""

import os
import subprocess
import time
from typing import Optional

class V4L2DeviceManager:
    def __init__(self, device: Optional[str] = None, card_label: str = "EasyWebcam"):
        self.device = device or "/dev/video0"
        self.card_label = card_label
        self.width = 0
        self.height = 0
        self.pixel_format = "YUYV"
        self._fd: Optional[int] = None
        self._we_loaded_module = False

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
                self._we_loaded_module = True
                # Give udev a moment to create the device node
                for _ in range(20):
                    if os.path.exists(self.device):
                        break
                    time.sleep(0.05)
            except Exception as e:
                print(f"[!] Error loading v4l2loopback: {e}")
                return False
        else:
            print(f"[*] Using existing v4l2loopback module on {self.device}...")

        if not os.path.exists(self.device):
            # Check what video devices exist
            import glob
            devs = glob.glob("/dev/video*")
            if devs:
                self.device = devs[0]
            else:
                print(f"[!] Failed to find created video device.")
                return False

        # Ensure user can read/write to the device without sudo
        try:
            subprocess.run(["sudo", "chmod", "666", self.device], check=False, capture_output=True)
        except Exception:
            pass

        print(f"[✓] Virtual webcam online: {self.device} ({self.card_label})")
        return True

    def setup_format(self, width: int, height: int, pixel_format: str = "YUYV") -> bool:
        """Sets resolution and pixel format via v4l2-ctl and opens device descriptor."""
        if self._fd is not None:
            try:
                os.close(self._fd)
            except Exception:
                pass
            self._fd = None

        self.width = width
        self.height = height
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
            self._fd = os.open(self.device, os.O_WRONLY | os.O_SYNC)
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

        if self._we_loaded_module:
            print(f"\n[*] Cleaning up: Removing {self.device} from system...")
            try:
                # Small delay to ensure any readers (Discord, etc.) release the file
                time.sleep(0.2)
                subprocess.run(["sudo", "modprobe", "-r", "v4l2loopback"], check=False, capture_output=True)
                print(f"[✓] Virtual webcam device removed. System clean.")
            except Exception as e:
                print(f"[!] Warning during module unload: {e}")
            self._we_loaded_module = False
