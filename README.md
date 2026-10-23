# OmniCam

Turn any smartphone (iOS / Android) into a high-performance wireless Linux webcam.  
**Zero apps installed on the phone. Clean video only. Interactive remote control from PC.**

[English](#english) | [Русский](#русский)

---

<a name="english"></a>
## English

OmniCam creates a clean virtual webcam device (`/dev/video0`) on your Linux system and streams low-latency video from your smartphone's browser via native WebRTC over local Wi-Fi.

### Key Features

* **Global CLI Utility:** Run `omnicam` directly from any terminal.
* **Interactive PC Remote Control:** Change resolution (`720`, `1080`), change framerate (`30`, `60`), or flip camera (`f` / `flip`) directly from your terminal keyboard while streaming.
* **Bilingual Support (EN / RU):** English by default, with one-click or one-command switch to Russian in both the CLI and the mobile web UI.
* **Aspect-Fit Guarantee:** Crisp 16:9 widescreen in landscape; undistorted pillarboxed framing with black bars in portrait mode. No stretching or tearing.
* **Accurate Diagnostics:** Real-time HUD showing both phone capture resolution and normalized output resolution.
* **Clean Hardware Lifecycle:** Dynamically loads the `v4l2loopback` kernel module on startup and automatically unloads it on exit. No ghost devices left behind.
* **Zero Mobile Apps:** Works out-of-the-box in Safari (iOS) and Chrome (Android). Simply scan the terminal QR code.
* **Strictly Video Only:** No virtual sound cards or dummy audio sinks created in PulseAudio / PipeWire.
* **Low Latency (~30-50ms):** Hardware-accelerated WebRTC streaming directly over your local network.

### Prerequisites

Install `v4l2loopback` and standard tools on Debian / Ubuntu / Linux Mint:
```bash
sudo apt update
sudo apt install -y v4l2loopback-dkms v4l2loopback-utils libgl1 python3-pip
```

### Installation

Clone the repository and install OmniCam:
```bash
git clone https://github.com/andrewbohachov/omnicam.git
cd omnicam
pip install -e .
```

To make the `omnicam` command available system-wide:
```bash
sudo ln -sf $(which omnicam) /usr/local/bin/omnicam
```

### Quick Usage

Run in your terminal:
```bash
omnicam
```

1. Scan the QR code displayed in the terminal using your phone camera.
2. Open the URL and tap **"START STREAM"**.
3. Select **"OmniCam"** as your camera in Discord, OBS Studio, Telegram, Zoom, or Google Meet.

### Interactive Terminal Commands

While streaming, type commands into the terminal prompt (`omnicam > `):

| Command | Description |
| :--- | :--- |
| `720` / `1080` | Switch phone camera resolution on the fly |
| `30` / `60` | Change target framerate |
| `f` or `flip` | Switch between Front and Rear camera |
| `t` or `torch` | Toggle smartphone flashlight (where supported) |
| `s` or `status` | Show live stream stats and framerate |
| `lang en` / `lang ru` | Switch CLI language |
| `h` or `help` | Show interactive commands list |
| `q` or `quit` | Exit OmniCam and unload virtual camera |

### Command-Line Arguments

```
omnicam [OPTIONS]

Options:
  -r, --res RES        Webcam output resolution: 1080 or 720 (default: 1080)
  --lang {en,ru}       Interface language (default: en)
  -p, --port PORT      HTTPS server port (default: 8443)
  -d, --device DEVICE  V4L2 target device (default: /dev/video0)
  -l, --label LABEL    Device display name (default: OmniCam)
  --ip IP              Manual local IP address override
  --keep-device        Do not unload v4l2loopback module on shutdown
  -h, --help           Show help message
```

#### Examples:
```bash
# Default launch (1080p, English)
omnicam

# Launch in 720p mode for lighter Wi-Fi bandwidth
omnicam -r 720

# Launch with Russian language
omnicam --lang ru

# Launch with custom device label
omnicam -l "Studio Cam"
```

---

<a name="русский"></a>
## Русский

OmniCam превращает любой смартфон (iOS / Android) в высокопроизводительную беспроводную веб-камеру для Linux без установки приложений на телефон.

### Основные возможности

* **Утилита для терминала:** Запуск командой `omnicam` из любой папки.
* **Управление с клавиатуры ПК:** Переключение разрешения (`720`, `1080`), FPS (`30`, `60`) и камер (`f` / `flip`) прямо из терминала во время стрима.
* **Поддержка двух языков (EN / RU):** Английский по умолчанию, переключение на русский одной кнопкой в веб-интерфейсе или параметром `--lang ru`.
* **Правильные пропорции (Aspect-Fit):** Честный широкоформатный 16:9 в горизонтальном положении и центрированное изображение с полями (pillarbox) в вертикальном. Без искажений и деформаций.
* **Честная диагностика:** Отображение реального разрешения захвата с телефона и выходного разрешения виртуальной камеры.
* **Чистый жизненный цикл:** Автоматическая загрузка модуля ядра `v4l2loopback` при старте и выгрузка при выходе. Никаких лишних фантомных устройств в системе.
* **Без приложений на телефоне:** Работает в Safari (iOS) и Chrome (Android) через встроенный WebRTC. Достаточно отсканировать QR-код.
* **Только видео:** Не создает виртуальных аудиоустройств и не засоряет микшер PulseAudio / PipeWire.
* **Минимальная задержка (~30-50 мс):** Прямая передача через локальную сеть по WebRTC.

### Системные требования

Установка `v4l2loopback` и необходимых библиотек в Debian / Ubuntu / Linux Mint:
```bash
sudo apt update
sudo apt install -y v4l2loopback-dkms v4l2loopback-utils libgl1 python3-pip
```

### Установка

Клонируйте репозиторий и установите пакет:
```bash
git clone https://github.com/andrewbohachov/omnicam.git
cd omnicam
pip install -e .
```

Для глобального доступа к команде `omnicam`:
```bash
sudo ln -sf $(which omnicam) /usr/local/bin/omnicam
```

### Быстрый запуск

Запустите в терминале:
```bash
omnicam
```

1. Наведите камеру телефона на QR-код в терминале.
2. Откройте ссылку в браузере и нажмите **"START STREAM"** (или **"НАЧАТЬ СТРИМ"**).
3. В Discord, OBS Studio, Telegram или Zoom выберите камеру **"OmniCam"**.

### Интерактивные команды в терминале

Во время стрима вводите команды в строку `omnicam > `:

| Команда | Описание |
| :--- | :--- |
| `720` / `1080` | Смена разрешения на лету |
| `30` / `60` | Изменение целевого FPS |
| `f` или `flip` | Переключение между фронтальной и основной камерой |
| `t` или `torch` | Включение / выключение фонарика (при поддержке устройством) |
| `s` или `status` | Показать статус потока, текущее разрешение и FPS |
| `lang en` / `lang ru` | Переключение языка интерфейса |
| `h` или `help` | Справка по командам |
| `q` или `quit` | Завершение работы и корректное удаление виртуального устройства |

### Параметры запуска

```
omnicam [ПАРАМЕТРЫ]

Параметры:
  -r, --res RES        Выходное разрешение: 1080 или 720 (по умолчанию: 1080)
  --lang {en,ru}       Язык интерфейса (по умолчанию: en)
  -p, --port PORT      Порт HTTPS сервера (по умолчанию: 8443)
  -d, --device DEVICE  Целевое V4L2 устройство (по умолчанию: /dev/video0)
  -l, --label LABEL    Имя камеры в приложениях (по умолчанию: OmniCam)
  --ip IP              Ручное указание локального IP адреса
  --keep-device        Не выгружать модуль v4l2loopback при выходе
  -h, --help           Показать справку
```

---

## License

MIT License. Free and open source.
