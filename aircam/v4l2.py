"""
AirCam - V4L2 Loopback Sink Manager
Controls /dev/videoX virtual webcam device and writes raw video frames.
"""

import os
import subprocess
import time
from typing import Optional

class V4L2Sink:
    def __init__(self, device: str = "/dev/video0"):
        self.device = device
        self.width = 0
        self.height = 0
        self.pixel_format = "YUYV"
        self._fd: Optional[int] = None

    def ensure_device(self, card_label: str = "AirCam (Wireless)") -> bool:
        """Checks if device exists, tries to load module if missing."""
        if not os.path.exists(self.device):
            try:
                subprocess.run(
                    [
                        "sudo", "modprobe", "v4l2loopback",
                        "exclusive_caps=1",
                        f"card_label={card_label}"
                    ],
                    check=True,
                    capture_output=True
                )
                time.sleep(0.3)
            except Exception as e:
                print(f"[!] Warning: Could not auto-load v4l2loopback: {e}")
                return False

        if os.path.exists(self.device):
            # Ensure permissions
            try:
                subprocess.run(["sudo", "chmod", "666", self.device], check=False)
            except Exception:
                pass
            return True
        return False

    def setup_format(self, width: int, height: int, pixel_format: str = "YUYV") -> bool:
        """Configures the V4L2 loopback output format."""
        if self._fd is not None:
            os.close(self._fd)
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
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"[!] Warning v4l2-ctl set format: {res.stderr.strip()}")
        except Exception as e:
            print(f"[!] v4l2-ctl error: {e}")

        # Open fd for writing
        try:
            self._fd = os.open(self.device, os.O_WRONLY | os.O_SYNC)
            return True
        except Exception as e:
            print(f"[!] Error opening {self.device}: {e}")
            return False

    def write_frame(self, raw_bytes: bytes) -> bool:
        """Writes raw frame buffer to the device."""
        if self._fd is None:
            return False
        try:
            os.write(self._fd, raw_bytes)
            return True
        except Exception as e:
            print(f"[!] Error writing frame: {e}")
            return False

    def close(self):
        """Closes the video device handle."""
        if self._fd is not None:
            try:
                os.close(self._fd)
            except Exception:
                pass
            self._fd = None
