<p align="center">
  <img src="src/resources/net.jeena.Recoder.svg" width="120" height="120" alt="Recoder logo">
</p>

# Recoder

**Recoder** is a clean and minimal video transcoder for Linux, designed for GNOME using GTK4 and libadwaita. It supports batch processing, drag-and-drop, and a straightforward user experience.

![Screenshot of Recoder](docs/screenshot-3.png)

## 📖 Help

See [docs/HELP.md](docs/HELP.md) for usage instructions and tips.

## ✨ Features

- Transcode multiple video files at once
- Drag-and-drop support for folders and files
- Modern libadwaita-based interface
- Toast notifications

## 📦 Installation

### Arch Linux

Recoder is available on the AUR:

```bash
yay -S recoder
```

### Flatpak

[Install Recoder Flatpak](https://jeena.github.io/recoder/net.jeena.Recoder.flatpakref)

After downloading the `net.jeena.Recoder.flatpakref` file, **double-click the file** or **open it with GNOME Software** to start the installation.

#### Install via Command Line

If you prefer, run these commands in a terminal:

```bash
flatpak install --user https://jeena.github.io/recoder/net.jeena.Recoder.flatpakref
flatpak run net.jeena.Recoder
```

## 📄 License

Recoder is licensed under the GNU General Public License v3.0.  
See [LICENSE](LICENSE) for details.
