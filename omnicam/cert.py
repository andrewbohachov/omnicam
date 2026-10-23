"""
OmniCam - SSL Certificate Generator
Generates self-signed certificates with SAN IP extension for local network HTTPS.
Mobile browsers require HTTPS to grant camera permissions.
"""

import os
import datetime
import ipaddress
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

CONFIG_DIR = Path.home() / ".config" / "omnicam"

def get_or_create_ssl_cert(local_ip: str) -> tuple[str, str]:
    """
    Returns paths to (cert_path, key_path).
    Generates new certificate if none exists or if IP changed.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cert_path = CONFIG_DIR / "cert.pem"
    key_path = CONFIG_DIR / "key.pem"
    ip_file = CONFIG_DIR / "last_ip.txt"

    if cert_path.exists() and key_path.exists() and ip_file.exists():
        if ip_file.read_text().strip() == local_ip:
            return str(cert_path), str(key_path)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    ip_obj = ipaddress.ip_address(local_ip)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "RU"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "OmniCam"),
        x509.NameAttribute(NameOID.COMMON_NAME, local_ip),
    ])

    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.IPAddress(ip_obj),
                x509.DNSName("localhost")
            ]),
            critical=False
        )
        .sign(key, hashes.SHA256())
    )

    with open(key_path, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    ip_file.write_text(local_ip)
    return str(cert_path), str(key_path)
