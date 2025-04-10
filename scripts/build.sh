#!/usr/bin/env bash

build_deb() {
  # https://www.devdungeon.com/content/debian-package-tutorial-dpkgdeb
  # that was really easy actually
  rm build -r
  mkdir build/deb -p
  python3 setup.py install --root=build/deb
  mv build/deb/usr/local/lib/python3.*/ build/deb/usr/lib/python3/
  cp ./DEBIAN build/deb/ -r
  mkdir dist -p
  rm dist/input-remapper-2.1.1.deb || true
  dpkg-deb -Z gzip -b build/deb dist/input-remapper-2.1.1.deb
}

build_deb &
# add more build targets here

wait
