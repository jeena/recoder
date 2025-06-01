# Recoder

**Recoder** is a GTK4-based GUI application for video transcoding. It provides a clean, modern interface using Libadwaita and integrates with `ffmpeg` to convert videos with ease.

![screenshot](resources/net.jeena.Recoder.png)

---

## ✨ Features

- Simple and elegant GTK4 interface
- Built with Libadwaita for a native GNOME look
- Supports common video formats using `ffmpeg`
- Lightweight and fast
- System notifications on task completion

---

## 🛠 Requirements

- Python 3.10+
- GTK4
- Libadwaita
- `ffmpeg`
- Python bindings:
  - `python-gobject`

---

## 🚀 Installation (Arch Linux)

```bash
git clone https://github.com/jeena/recoder.git
cd recoder
makepkg -si
```

This will install Recoder system-wide using Pacman, so you can later remove it cleanly:

```bash
sudo pacman -R recoder
```

---

## 🧪 Development Setup

If you're hacking on Recoder:

```bash
git clone https://github.com/jeena/recoder.git
cd recoder
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Then run:

```bash
recoder
```

---

## 📁 Project Structure

```
src/
└── recoder/
    ├── app.py
    ├── config.py
    ├── models.py
    ├── transcoder_worker.py
    └── ui.py
resources/
├── net.jeena.Recoder.desktop
└── net.jeena.Recoder.png
```

---

## 📦 Packaging

Recoder follows modern Python packaging using `pyproject.toml` and `setuptools`. The Arch package installs Python modules to `site-packages` and the desktop file + icon in appropriate locations.

---

## 📄 License

Licensed under the GPLv3. See `LICENSE` for details.

---

## 👤 Author

Made by Jeena · [github.com/jeena](https://github.com/jeena)