# Maintainer: Jeena <your-email@example.com>
pkgname=recoder
pkgver=1.0.0
pkgrel=1
pkgdesc="A GTK4 video transcoding GUI application"
arch=('x86_64' 'aarch64')
url="https://github.com/jeena/recoder"
license=('GPL3')
depends=(
    'gtk4' 
    'libadwaita' 
    'gobject-introspection-runtime' 
    'python' 
    'python-gobject' 
    'ffmpeg'
)
optdepends=(
  'libcanberra: play system notification sounds'
  'sound-theme-freedesktop: standard system sounds like "complete.oga"'
)
makedepends=('python-setuptools')
source=()
sha256sums=()

package() {
    install -Dm755 "../src/app.py" "$pkgdir/usr/bin/recoder"
    install -Dm644 "../src/config.py" "$pkgdir/usr/lib/recoder/config.py"
    install -Dm644 "../src/models.py" "$pkgdir/usr/lib/recoder/models.py"
    install -Dm644 "../src/transcoder_worker.py" "$pkgdir/usr/lib/recoder/transcoder_worker.py"
    install -Dm644 "../src/ui.py" "$pkgdir/usr/lib/recoder/ui.py"
    install -Dm644 "../resources/net.jeena.Recoder.desktop" "$pkgdir/usr/share/applications/net.jeena.Recoder.desktop"
    install -Dm644 "../resources/net.jeena.Recoder.png" "$pkgdir/usr/share/icons/hicolor/256x256/apps/net.jeena.Recoder.png"
    install -Dm644 "../src/__init__.py" "$pkgdir/usr/lib/recoder/__init__.py"
}
