#!/usr/bin/env bash
set -e

VERSION="0.1.0"
PACKAGE_NAME="omnicam"
BUILD_DIR="/tmp/${PACKAGE_NAME}_${VERSION}_all"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Building .deb package for Debian / Ubuntu ==="

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/opt/omnicam"
mkdir -p "$BUILD_DIR/usr/bin"

# Control file
cat <<EOF > "$BUILD_DIR/DEBIAN/control"
Package: ${PACKAGE_NAME}
Version: ${VERSION}
Section: video
Priority: optional
Architecture: all
Depends: python3, python3-pip, python3-venv, v4l2loopback-dkms, v4l2loopback-utils, libgl1
Maintainer: Andrew Bohachov <https://github.com/andrewbohachov/omnicam>
Description: OmniCam - Turn any smartphone into a wireless Linux webcam
 Zero apps on phone, clean video only, WebRTC low latency,
 interactive PC remote control, and clean hardware lifecycle.
EOF

# Postinst script: initialize venv and install dependencies
cat <<'EOF' > "$BUILD_DIR/DEBIAN/postinst"
#!/usr/bin/env bash
set -e

VENV_DIR="/opt/omnicam/venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet /opt/omnicam
chmod -R a+rX /opt/omnicam

exit 0
EOF
chmod 755 "$BUILD_DIR/DEBIAN/postinst"

# Postrm script: cleanup /opt/omnicam on purge/remove
cat <<'EOF' > "$BUILD_DIR/DEBIAN/postrm"
#!/usr/bin/env bash
set -e

if [ "$1" = "purge" ] || [ "$1" = "remove" ]; then
    rm -rf /opt/omnicam
fi

exit 0
EOF
chmod 755 "$BUILD_DIR/DEBIAN/postrm"

# Launcher wrapper in /usr/bin/omnicam
cat <<'EOF' > "$BUILD_DIR/usr/bin/omnicam"
#!/usr/bin/env bash
exec /opt/omnicam/venv/bin/omnicam "$@"
EOF
chmod 755 "$BUILD_DIR/usr/bin/omnicam"

# Copy project files to /opt/omnicam
cp -r "$SCRIPT_DIR/omnicam" "$BUILD_DIR/opt/omnicam/"
cp "$SCRIPT_DIR/pyproject.toml" "$BUILD_DIR/opt/omnicam/"
cp "$SCRIPT_DIR/requirements.txt" "$BUILD_DIR/opt/omnicam/"
cp "$SCRIPT_DIR/LICENSE" "$BUILD_DIR/opt/omnicam/"
cp "$SCRIPT_DIR/README.md" "$BUILD_DIR/opt/omnicam/"

# Build deb package
OUTPUT_DEB="${SCRIPT_DIR}/${PACKAGE_NAME}_${VERSION}_all.deb"
dpkg-deb --build --root-owner-group "$BUILD_DIR" "$OUTPUT_DEB"
rm -rf "$BUILD_DIR"

echo "[OK] Package successfully built: $OUTPUT_DEB"
echo "  Install on any Ubuntu/Debian system via:"
echo "    sudo apt install ./${PACKAGE_NAME}_${VERSION}_all.deb"
