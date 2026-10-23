# 📷 OmniCam

> Turn any smartphone (iOS / Android) into a high-performance wireless Linux webcam.  
> **Zero apps installed on the phone. Clean video only. Interactive remote control from PC.**

---

## ⚡ Highlights

* **Global CLI Utility:** Run `omnicam` directly from any terminal.
* **Interactive PC Remote Control:** Change resolution (`720`, `1080`), change FPS (`30`, `60`), or flip camera (`f` / `flip`) directly from your Linux keyboard while streaming!
* **Aspect-Fit Guarantee:** Perfect 16:9 widescreen in landscape; clean, undistorted pillarboxing in portrait orientation.
* **Accurate HUD & Diagnostics:** Displays both the phone's native capture resolution and the normalized output resolution in real-time.
* **Clean Hardware Lifecycle:** Creates the virtual camera `/dev/video0` on startup and unloads it on shutdown.
* **Zero Apps on Phone:** Works in Safari (iOS) and Chrome (Android). Just scan the terminal QR code.
* **Strictly Video Only:** No virtual sound cards, no PulseAudio/PipeWire sink pollution.
* **Low Latency (~30–50ms):** Native hardware-accelerated **WebRTC** (H.264/VP8) streaming directly over your local Wi-Fi.

---

## 🚀 Quick Usage

In any terminal:

```bash
omnicam
```

1. Scan the **ANSI QR code** with your phone's camera.
2. Tap **"START STREAM"** on your phone.
3. In Discord, OBS, or Telegram, select **"OmniCam"**.

---

## 🎮 Interactive Terminal Commands

While streaming, you can type commands directly into the Linux terminal at the `omnicam > ` prompt:

| Command | Action |
| :--- | :--- |
| `720` / `1080` | Switch phone camera resolution on the fly |
| `30` / `60` | Change target framerate |
| `f` or `flip` | Flip between Front (Selfie) and Rear camera |
| `t` or `torch` | Toggle phone flashlight (where supported) |
| `s` or `status` | Show live stream stats and FPS |
| `h` or `help` | Show commands cheat sheet |
| `q` or `quit` | Stop stream and clean up device |

---

## ⚙️ Options & Arguments

```bash
omnicam [OPTIONS]

Options:
  -r, --res RES        Webcam output resolution: 1080 or 720 (default: 1080)
  -p, --port PORT      HTTPS server port (default: 8443)
  -d, --device DEVICE  V4L2 target device (default: /dev/video0)
  -l, --label LABEL    Device display name (default: OmniCam)
  --ip IP              Manual local IP override
  --keep-device        Do not unload v4l2loopback on shutdown
  -h, --help           Show help message
```

### Examples:
```bash
# Default: 1080p Full HD output
omnicam

# Launch with 720p output for lighter load / slower Wi-Fi
omnicam -r 720

# Run with custom camera name
omnicam -r 1080 -l "Pixel 8 Pro Cam"
```

---

## 📄 License

MIT License. Free and open source.
