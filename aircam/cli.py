"""
AirCam CLI Entry Point
Finds network IP, prints ANSI QR code in terminal, and starts the wireless streaming server.
"""

import sys
import ssl
import socket
import argparse
import asyncio
from aiohttp import web
import qrcode
from .cert import get_or_create_ssl_cert
from .v4l2 import V4L2Sink
from .server import AirCamServer

def get_primary_local_ip() -> str:
    """Finds the primary local LAN IP connected to default gateway."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to be reachable, just triggers routing table lookup
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
        prog="aircam",
        description="AirCam: Turn any smartphone into a wireless Linux webcam (zero apps on phone, clean video only)."
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
        help="Target V4L2 loopback device (default: /dev/video0)"
    )
    parser.add_argument(
        "--ip",
        type=str,
        default=None,
        help="Custom IP address override"
    )
    return parser.parse_args()

def main():
    args = parse_args()
    local_ip = args.ip or get_primary_local_ip()
    port = args.port
    device = args.device

    print("=========================================================")
    print("  🚀 AirCam: Wireless Phone Webcam for Linux")
    print("=========================================================")
    print(f"[*] Target Video Device : {device}")
    print(f"[*] Local Network IP    : {local_ip}")
    print(f"[*] Web Server Port     : {port}")

    # Initialize V4L2 Sink
    sink = V4L2Sink(device=device)
    if not sink.ensure_device():
        print(f"[!] Note: Please ensure {device} is available with v4l2loopback.")
        print(f"    Run: sudo modprobe v4l2loopback exclusive_caps=1 card_label=\"AirCam\"")

    # Generate or retrieve SSL Cert
    print("[*] Generating local SSL certificate...")
    cert_path, key_path = get_or_create_ssl_cert(local_ip)

    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)

    def on_stats(stats):
        sys.stdout.write(
            f"\r[📹 STREAMING] Resolution: {stats['width']}x{stats['height']} | "
            f"FPS: {stats['fps']} | Total Frames: {stats['frames']}   "
        )
        sys.stdout.flush()

    server = AirCamServer(sink=sink, on_stats_update=on_stats)

    url = f"https://{local_ip}:{port}"
    print("\n---------------------------------------------------------")
    print(f"📱 SCAN THIS QR CODE WITH YOUR PHONE (iOS / Android):")
    print("---------------------------------------------------------")
    try:
        print_qr_code(url)
    except Exception:
        pass
    print(f"\n👉 Or open directly in your phone's browser:")
    print(f"   {url}")
    print("---------------------------------------------------------")
    print("💡 Note for first connection:")
    print("   1. Since this is a local self-signed certificate, tap")
    print("      'Advanced' -> 'Proceed to site' in Chrome / Safari.")
    print("   2. Tap 'Allow' when the browser asks for camera access.")
    print("   3. Your video will immediately stream to /dev/video0!")
    print("   4. In Discord, OBS, or Chrome, select: 'AirCam' or 'PhoneCam'")
    print("---------------------------------------------------------\n")

    try:
        web.run_app(server.app, host="0.0.0.0", port=port, ssl_context=ssl_context, print=None)
    except KeyboardInterrupt:
        print("\n\n[*] Shutting down AirCam cleanly...")
    finally:
        asyncio.run(server.cleanup())
        print("[*] Done. Goodbye!")

if __name__ == "__main__":
    main()
