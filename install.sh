#!/usr/bin/env bash
set -e

# ==============================================================================
# OmniCam One-Line Installer
# Supports local execution and remote curl execution:
#   curl -fsSL https://raw.githubusercontent.com/andrewbohachov/omnicam/main/install.sh | bash
# ==============================================================================

REPO_URL="https://github.com/andrewbohachov/omnicam.git"
INSTALL_DIR="${HOME}/.local/share/omnicam"
BIN_DIR="${HOME}/.local/bin"

echo "=========================================================="
echo "               OMNICAM INSTALLER                          "
echo "=========================================================="

mkdir -p "$BIN_DIR"
mkdir -p "${HOME}/.local/share"

# [1/4] Install system dependencies (v4l2loopback, python3-venv, etc.)
echo "[1/4] Checking system dependencies..."
if command -v apt-get &>/dev/null; then
    MISSING_PKGS=""
    for pkg in v4l2loopback-dkms v4l2loopback-utils python3 python3-pip python3-venv libgl1; do
        if ! dpkg -s "$pkg" &>/dev/null; then
            MISSING_PKGS="$MISSING_PKGS $pkg"
        fi
    done
    if [ -n "$MISSING_PKGS" ]; then
        echo "[*] Installing missing system packages:$MISSING_PKGS"
        sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y $MISSING_PKGS
    else
        echo "[*] System packages already satisfied."
    fi
elif command -v pacman &>/dev/null; then
    if ! pacman -Qi v4l2loopback-dkms &>/dev/null && ! pacman -Qi v4l2loopback-hook &>/dev/null; then
        echo "[*] Installing v4l2loopback on Arch Linux..."
        sudo pacman -S --needed --noconfirm v4l2loopback-dkms v4l2loopback-utils python python-pip
    fi
elif command -v dnf &>/dev/null; then
    if ! rpm -q v4l2loopback &>/dev/null; then
        echo "[*] Installing v4l2loopback on Fedora..."
        sudo dnf install -y v4l2loopback python3 python3-pip
    fi
fi

# [2/4] Setup OmniCam source code
echo "[2/4] Setting up OmniCam source files..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

if [ -f "$SCRIPT_DIR/pyproject.toml" ] && [ -d "$SCRIPT_DIR/omnicam" ]; then
    echo "[*] Installing from local repository ($SCRIPT_DIR)..."
    rm -rf "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
    cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/" 2>/dev/null || true
    cp "$SCRIPT_DIR"/.* "$INSTALL_DIR/" 2>/dev/null || true
else
    echo "[*] Cloning latest OmniCam repository from GitHub..."
    if [ -d "$INSTALL_DIR/.git" ]; then
        git -C "$INSTALL_DIR" pull --quiet
    else
        rm -rf "$INSTALL_DIR"
        git clone --quiet "$REPO_URL" "$INSTALL_DIR"
    fi
fi

# [3/4] Create virtualenv and install dependencies
echo "[3/4] Preparing isolated virtual environment..."
VENV_DIR="$INSTALL_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -e "$INSTALL_DIR"

# Create binary launcher wrapper in ~/.local/bin
cat <<EOF > "$BIN_DIR/omnicam"
#!/usr/bin/env bash
exec "$VENV_DIR/bin/omnicam" "\$@"
EOF
chmod +x "$BIN_DIR/omnicam"

# Create global symlink in /usr/local/bin if possible
if [ -w /usr/local/bin ]; then
    ln -sf "$BIN_DIR/omnicam" /usr/local/bin/omnicam 2>/dev/null || true
elif command -v sudo &>/dev/null; then
    sudo ln -sf "$BIN_DIR/omnicam" /usr/local/bin/omnicam 2>/dev/null || true
fi

# [4/4] Verify PATH
echo "[4/4] Verifying PATH..."
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    ADDED_TO=""
    if [ -f "$HOME/.bashrc" ] && ! grep -q 'HOME/\.local/bin' "$HOME/.bashrc" && ! grep -q '\$HOME/\.local/bin' "$HOME/.bashrc"; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        ADDED_TO="~/.bashrc"
    fi
    if [ -f "$HOME/.zshrc" ] && ! grep -q 'HOME/\.local/bin' "$HOME/.zshrc" && ! grep -q '\$HOME/\.local/bin' "$HOME/.zshrc"; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
        ADDED_TO="${ADDED_TO:+$ADDED_TO, }~/.zshrc"
    fi
    if [ -n "$ADDED_TO" ]; then
        echo "[*] Added $BIN_DIR to PATH in $ADDED_TO."
    fi
fi

echo ""
echo "=========================================================="
echo "               OMNICAM SUCCESSFULLY INSTALLED            "
echo "=========================================================="
echo ""
echo "Run anywhere in terminal:"
echo "  omnicam"
echo ""
echo "Command examples:"
echo "  omnicam              # Default 1080p, English"
echo "  omnicam -r 720       # 720p mode"
echo "  omnicam --lang ru    # Russian language"
echo "  omnicam --help       # Full options list"
echo "=========================================================="
