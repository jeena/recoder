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
makedepends=(
    'python-setuptools'
    'python-build'
    'python-installer'
)
source=()
sha256sums=()

build() {
    cd "$srcdir"
    python -m build --wheel
}

package() {
    cd "$srcdir"
    python -m installer --destdir="$pkgdir" dist/*.whl

    install -Dm644 resources/net.jeena.Recoder.desktop \
        "$pkgdir/usr/share/applications/net.jeena.Recoder.desktop"
    install -Dm644 resources/net.jeena.Recoder.png \
        "$pkgdir/usr/share/icons/hicolor/256x256/apps/net.jeena.Recoder.png"
}