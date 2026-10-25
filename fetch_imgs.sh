#!/bin/bash
# Pull generated illustrations from the `assets` branch into the working tree (days/.../img/*.jpg).
set -e
cd "$(dirname "$0")"
rm -rf /tmp/assets_fetch && git clone -q --depth 1 -b assets https://github.com/ayyub1nnat/money-channel-videos /tmp/assets_fetch
for d in "$@"; do mkdir -p "$d/img"; cp /tmp/assets_fetch/$d/img/*.jpg "$d/img/" 2>/dev/null || true; echo "$d: $(ls $d/img | wc -l) images"; done
