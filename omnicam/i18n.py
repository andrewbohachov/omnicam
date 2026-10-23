"""
OmniCam - Internationalization (i18n)
Supports English (default) and Russian.
No emojis.
"""

STRINGS = {
    "en": {
        "title": "OmniCam - Wireless Phone Webcam for Linux",
        "device_created": "[*] Dynamically creating virtual webcam ({label})...",
        "device_active": "[*] Virtual webcam module active on {device}...",
        "device_online": "[OK] Virtual webcam online: {device} ({label}) [{res}]",
        "cert_gen": "[*] Generating local SSL certificate...",
        "scan_qr": "[SCAN] Scan this QR code with your phone camera:",
        "or_open": "[URL] Or open directly in your phone's browser:",
        "tip_select": "[INFO] Select '{label}' in Discord, OBS, Telegram, or Zoom.",
        "tip_commands": "[INFO] Type 'help' for commands, 'status' for stats, or 'q' to exit.",
        "tip_cleanup": "[INFO] Virtual device will be cleanly removed when you press Ctrl+C or type 'q'.",
        "stream_active": "\n  [STREAM ACTIVE] Phone: {phone_w}x{phone_h} -> Output: {out_w}x{out_h} @ {fps} FPS\n",
        "status_waiting": "  [STATUS] Waiting for phone to connect...",
        "status_info": "  [STATUS] Phone: {phone_w}x{phone_h} | Output: {out_w}x{out_h} | FPS: {fps} | Total Frames: {frames}",
        "remote_res": "  [REMOTE] Switching phone camera to {val}...",
        "remote_fps": "  [REMOTE] Setting phone framerate to {val} FPS...",
        "remote_flip": "  [REMOTE] Flipping camera (Front <-> Rear)...",
        "remote_torch": "  [REMOTE] Toggling flashlight...",
        "help_header": "\n--- [Interactive Commands] ---",
        "help_res": "  720 / 1080   : Change resolution (strictly 16:9 widescreen)",
        "help_fps": "  30 / 60      : Change FPS",
        "help_flip": "  f / flip     : Switch Front / Rear camera",
        "help_torch": "  t / torch    : Toggle Flashlight",
        "help_status": "  s / status   : Show current stream status & FPS",
        "help_lang": "  lang [en/ru] : Switch CLI language",
        "help_exit": "  q / quit     : Exit OmniCam cleanly",
        "unknown_cmd": "  [!] Unknown command: '{cmd}'. Type 'help' for options.",
        "exiting": "\n[*] Exiting...",
        "cleanup_start": "\n[*] Cleaning up: Removing {device} from system...",
        "cleanup_done": "[OK] Virtual webcam device removed. System clean.",
        "cleanup_locked": "[!] Notice: {device} is currently kept open by PID {pid} (e.g. Discord camera preview).\n    Once you close the camera preview in that app, the device will be released.",
        "goodbye": "[*] Goodbye!",
        "lang_switched": "  [LANGUAGE] Language set to: English",
    },
    "ru": {
        "title": "OmniCam - Беспроводная веб-камера из смартфона для Linux",
        "device_created": "[*] Создание виртуальной веб-камеры ({label})...",
        "device_active": "[*] Модуль виртуальной веб-камеры активен на {device}...",
        "device_online": "[OK] Виртуальная камера готова: {device} ({label}) [{res}]",
        "cert_gen": "[*] Генерация локального SSL-сертификата...",
        "scan_qr": "[SCAN] Отсканируйте этот QR-код камерой телефона:",
        "or_open": "[URL] Или откройте напрямую в браузере телефона:",
        "tip_select": "[INFO] Выберите '{label}' в Discord, OBS, Telegram или Zoom.",
        "tip_commands": "[INFO] Введите 'help' для списка команд, 'status' для статистики, или 'q' для выхода.",
        "tip_cleanup": "[INFO] Виртуальное устройство удалится при выходе (Ctrl+C или 'q').",
        "stream_active": "\n  [СТРИМ АКТИВЕН] Телефон: {phone_w}x{phone_h} -> Выход: {out_w}x{out_h} @ {fps} FPS\n",
        "status_waiting": "  [СТАТУС] Ожидание подключения смартфона...",
        "status_info": "  [СТАТУС] Телефон: {phone_w}x{phone_h} | Выход: {out_w}x{out_h} | FPS: {fps} | Всего кадров: {frames}",
        "remote_res": "  [УПРАВЛЕНИЕ] Переключение разрешения телефона на {val}...",
        "remote_fps": "  [УПРАВЛЕНИЕ] Установка частоты кадров телефона: {val} FPS...",
        "remote_flip": "  [УПРАВЛЕНИЕ] Переключение камеры (Фронтальная <-> Задняя)...",
        "remote_torch": "  [УПРАВЛЕНИЕ] Переключение фонарика...",
        "help_header": "\n--- [Интерактивные команды] ---",
        "help_res": "  720 / 1080   : Сменить разрешение (строго 16:9)",
        "help_fps": "  30 / 60      : Сменить FPS",
        "help_flip": "  f / flip     : Переключить камеру (Фронтальная / Задняя)",
        "help_torch": "  t / torch    : Включить / выключить фонарик",
        "help_status": "  s / status   : Показать статус стрима и FPS",
        "help_lang": "  lang [en/ru] : Переключить язык консоли",
        "help_exit": "  q / quit     : Выйти из OmniCam с удалением устройства",
        "unknown_cmd": "  [!] Неизвестная команда: '{cmd}'. Введите 'help' для справки.",
        "exiting": "\n[*] Завершение работы...",
        "cleanup_start": "\n[*] Очистка: Удаление {device} из системы...",
        "cleanup_done": "[OK] Виртуальное устройство удалено. Система чиста.",
        "cleanup_locked": "[!] Внимание: {device} удерживается процессом PID {pid} (например, Discord).\n    Как только вы закроете предпросмотр камеры в этой программе, устройство освободится.",
        "goodbye": "[*] До свидания!",
        "lang_switched": "  [ЯЗЫК] Установлен русский язык",
    }
}

class I18n:
    def __init__(self, lang: str = "en"):
        self.lang = "ru" if lang.lower().startswith("ru") else "en"

    def set_lang(self, lang: str):
        self.lang = "ru" if lang.lower().startswith("ru") else "en"

    def get(self, key: str, **kwargs) -> str:
        text = STRINGS.get(self.lang, STRINGS["en"]).get(key, STRINGS["en"].get(key, key))
        if kwargs:
            return text.format(**kwargs)
        return text

i18n = I18n("en")
