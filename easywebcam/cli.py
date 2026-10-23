"""
EasyWebcam CLI Entry Point
Finds network IP, sets up virtual webcam, prints ANSI QR code, and starts the server.
Includes interactive CLI commands to control resolution, FPS, and camera flip from the PC.
"""

import sys
import ssl
import socket
import threading
import argparse
import asyncio
from aiohttp import web
import qrcode
from .cert import get_or_create_ssl_cert
from .v4l2 import V4L2DeviceManager
from .server import EasyWebcamServer

def get_primary_local_ip() -> str:
    """Finds the primary local LAN IP connected to default gateway."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def print_qr_code(url: str):
    """Prints a crisp Unicode/ANSI QR code directly in the terminal."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)

def parse_args():
    parser = argparse.ArgumentParser(
        prog="easywebcam",
        description="EasyWebcam: Turn your smartphone into a clean, zero-lag Linux webcam with zero apps on phone."
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=8443,
        help="HTTPS server port (default: 8443)"
    )
    parser.add_argument(
        "-d", "--device",
        type=str,
        default="/dev/video0",
        help="Target V4L2 device (default: /dev/video0)"
    )
    parser.add_argument(
        "-l", "--label",
        type=str,
        default="EasyWebcam",
        help="Webcam name shown in Discord/OBS/browsers (default: EasyWebcam)"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1280,
        help="Target webcam width (default: 1280)"
    )
    parser.add_argument(
        "--height",
        type=int,
        default=720,
        help="Target webcam height (default: 720)"
    )
    parser.add_argument(
        "--ip",
        type=str,
        default=None,
        help="Manual IP address override"
    )
    parser.add_argument(
        "--keep-device",
        action="store_true",
        help="Do not unload the v4l2loopback module on exit"
    )
    return parser.parse_args()

def setup_cli_input_thread(server: EasyWebcamServer, loop: asyncio.AbstractEventLoop, stop_event: threading.Event):
    """Reads interactive terminal commands from the user while streaming."""
    def input_worker():
        while not stop_event.is_set():
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                cmd = line.strip().lower()
                if not cmd:
                    continue

                if cmd in ["720", "res 720", "720p"]:
                    print("\n[🎮 REMOTE] Switching phone camera to 720p...")
                    asyncio.run_coroutine_threadsafe(server.broadcast_command("set_res", "720"), loop)
                elif cmd in ["1080", "res 1080", "1080p"]:
                    print("\n[🎮 REMOTE] Switching phone camera to 1080p...")
                    asyncio.run_coroutine_threadsafe(server.broadcast_command("set_res", "1080"), loop)
                elif cmd in ["4k", "res 4k", "2160"]:
                    print("\n[🎮 REMOTE] Switching phone camera to 4K...")
                    asyncio.run_coroutine_threadsafe(server.broadcast_command("set_res", "4k"), loop)
                elif cmd in ["30", "fps 30", "30fps"]:
                    print("\n[🎮 REMOTE] Setting phone framerate to 30 FPS...")
                    asyncio.run_coroutine_threadsafe(server.broadcast_command("set_fps", 30), loop)
                elif cmd in ["60", "fps 60", "60fps"]:
                    print("\n[🎮 REMOTE] Setting phone framerate to 60 FPS...")
                    asyncio.run_coroutine_threadsafe(server.broadcast_command("set_fps", 60), loop)
                elif cmd in ["f", "flip", "cam"]:
                    print("\n[🎮 REMOTE] Flipping camera (Front ⇄ Rear)...")
                    asyncio.run_coroutine_threadsafe(server.broadcast_command("flip"), loop)
                elif cmd in ["t", "torch", "flash"]:
                    print("\n[🎮 REMOTE] Toggling flashlight...")
                    asyncio.run_coroutine_threadsafe(server.broadcast_command("torch"), loop)
                elif cmd in ["h", "help", "?"]:
                    print("\n--- [🎮 Interactive Commands] ---")
                    print("  720 / 1080 / 4k : Change resolution")
                    print("  30 / 60         : Change FPS")
                    print("  f / flip        : Switch Front / Rear camera")
                    print("  t / torch       : Toggle Flashlight")
                    print("  q / quit        : Exit EasyWebcam")
                    print("---------------------------------\n")
                elif cmd in ["q", "quit", "exit"]:
                    print("\n[*] Exiting...")
                    loop.call_soon_threadsafe(loop.stop)
                    break
                else:
                    print(f"\n[!] Unknown command: '{cmd}'. Type 'help' for options.")
            except Exception:
                break

    t = threading.Thread(target=input_worker, daemon=True)
    t.start()
    return t

def main():
    args = parse_args()
    local_ip = args.ip or get_primary_local_ip()
    port = args.port
    device = args.device
    card_label = args.label
    width = args.width
    height = args.height

    print("=========================================================")
    print(f"  📷 EasyWebcam — Phone Webcam for Linux")
    print("=========================================================")

    # Initialize device manager
    device_mgr = V4L2DeviceManager(device=device, card_label=card_label, width=width, height=height)
    if not device_mgr.start():
        print(f"[!] Critical: Could not initialize {device} via v4l2loopback.")
        sys.exit(1)

    if args.keep_device:
        device_mgr._keep_device = True

    # Generate or retrieve SSL Cert
    print("[*] Generating local SSL certificate...")
    cert_path, key_path = get_or_create_ssl_cert(local_ip)

    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)

    def on_stats(stats):
        sys.stdout.write(
            f"\r[📹 STREAMING] Phone: {stats['phone_w']}x{stats['phone_h']} | "
            f"Output: {stats['out_w']}x{stats['out_h']} | "
            f"FPS: {stats['fps']} | Total Frames: {stats['frames']}   "
        )
        sys.stdout.flush()

    server = EasyWebcamServer(sink=device_mgr, on_stats_update=on_stats)

    url = f"https://{local_ip}:{port}"
    print("\n---------------------------------------------------------")
    print("📱 SCAN THIS QR CODE WITH YOUR PHONE CAMERA:")
    print("---------------------------------------------------------")
    try:
        print_qr_code(url)
    except Exception:
        pass
    print(f"\n👉 Or open directly in your phone's browser:")
    print(f"   {url}")
    print("---------------------------------------------------------")
    print(f"💡 Select '{card_label}' in Discord, OBS, Telegram, or Zoom.")
    print("💡 Interactive PC commands: Type '720', '1080', '30', '60', 'flip', or 'help'")
    print("💡 Virtual device will be cleanly removed when you press Ctrl+C or type 'q'.")
    print("---------------------------------------------------------\n")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    stop_event = threading.Event()

    setup_cli_input_thread(server, loop, stop_event)

    app_runner = web.AppRunner(server.app)
    loop.run_until_complete(app_runner.setup())
    site = web.TCPSite(app_runner, host="0.0.0.0", port=port, ssl_context=ssl_context)
    loop.run_until_complete(site.start())

    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        stop_event.set()
        loop.run_until_complete(app_runner.cleanup())
        loop.run_until_complete(server.cleanup())
        print("[*] Goodbye!")

if __name__ == "__main__":
    main()
