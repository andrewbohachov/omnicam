"""
EasyWebcam CLI Entry Point
Finds network IP, sets up virtual webcam, prints ANSI QR code, and starts the server.
Cleans up and removes the virtual webcam device on shutdown.
"""

import sys
import ssl
import socket
import signal
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

def main():
    args = parse_args()
    local_ip = args.ip or get_primary_local_ip()
    port = args.port
    device = args.device
    card_label = args.label

    print("=========================================================")
    print(f"  📷 EasyWebcam — Phone Webcam for Linux")
    print("=========================================================")

    # Initialize and dynamically create the virtual webcam device
    device_mgr = V4L2DeviceManager(device=device, card_label=card_label)
    if not device_mgr.start():
        print(f"[!] Critical: Could not initialize {device} via v4l2loopback.")
        sys.exit(1)

    if args.keep_device:
        device_mgr._we_loaded_module = False

    # Generate or retrieve SSL Cert
    print("[*] Generating local SSL certificate...")
    cert_path, key_path = get_or_create_ssl_cert(local_ip)

    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)

    def on_stats(stats):
        sys.stdout.write(
            f"\r[📹 STREAMING] {stats['width']}x{stats['height']} | "
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
    print("💡 Virtual device will be cleanly removed when you press Ctrl+C.")
    print("---------------------------------------------------------\n")

    try:
        web.run_app(server.app, host="0.0.0.0", port=port, ssl_context=ssl_context, print=None)
    except (KeyboardInterrupt, SystemExit):
        print("\n[*] Stopping EasyWebcam...")
    finally:
        asyncio.run(server.cleanup())
        print("[*] Goodbye!")

if __name__ == "__main__":
    main()
