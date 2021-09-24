#!/bin/sh

set -e
mkdir -p vendor
cd vendor

# https command from https://httpie.org/
https -d https://github.com/WuLiFang/cgtwq/archive/v3.3.2.tar.gz -o cgtwq.tar.gz
https -d https://github.com/WuLiFang/wlf/archive/v0.6.0.tar.gz -o wlf.tar.gz
