pkgname=recoder
pkgver=1.0
pkgrel=1
pkgdesc="GTK4/libadwaita Video Recoder for DaVinci Resolve"
arch=('any')
url="https://example.com"
license=('MIT')
depends=('python' 'python-gobject' 'gtk4' 'libadwaita')
source=('recoder.py' 'recoder.desktop')
sha256sums=('SKIP' 'SKIP')

package() {
    install -Dm755 "recoder.py" "$pkgdir/usr/bin/recoder"
    install -Dm644 "recoder.desktop" "$pkgdir/usr/share/applications/recoder.desktop"
}
