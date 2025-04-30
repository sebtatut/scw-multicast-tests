#!/bin/bash
set -e

ROLE="$1"
BASE_IFACE="$2"
VLAN_ID="$3"

# dependencies
apt update && apt install -y \
  ffmpeg \
  iputils-ping \
  cmake \
  build-essential \
  pkg-config \
  libssl-dev \
  tshark \
  net-tools \
  smcroute \
  wget \
  git

# clone and build SRT v1.5.4 (required by TSDuck)
if [ ! -d srt ]; then
  git clone https://github.com/Haivision/srt.git
fi

cd srt
git fetch --all
git checkout v1.5.4

mkdir -p build
cd build
cmake ..
make -j"$(nproc)"
make install
ldconfig
cd ../..

# install TSDuck
TSDUCK_DEB="tsduck_3.33-3139.ubuntu22_amd64.deb"
if [ ! -f "$TSDUCK_DEB" ]; then
  wget "https://github.com/tsduck/tsduck/releases/download/v3.33-3139/$TSDUCK_DEB"
fi

apt install -y ./"$TSDUCK_DEB"

# sender specific -> create VLAN interface if specified
if [ "$ROLE" == "sender" ]; then
  if [ -z "$BASE_IFACE" ] || [ -z "$VLAN_ID" ]; then
    echo "[ERROR] Usage for sender: sudo ./install.sh sender <interface> <vlan_id>"
    exit 1
  fi

  VLAN_IFACE="$BASE_IFACE.$VLAN_ID"

  echo "[INFO] Creating VLAN interface: $VLAN_IFACE"
  ip link add link "$BASE_IFACE" name "$VLAN_IFACE" type vlan id "$VLAN_ID"
  ip link set "$VLAN_IFACE" up
  dhclient "$VLAN_IFACE"
fi

# autodetect private/UP iface, exclude docker
IFACE=$(ip -o -4 addr show up | awk '
  $2 !~ /^docker/ &&
  ($4 ~ /^10\./ || $4 ~ /^192\.168\./ || ($4 ~ /^172\./ && $4 ~ /^172\.(1[6-9]|2[0-9]|3[0-1])\./)) {
    print $2; exit
  }
')

if [ -z "$IFACE" ]; then
  echo "[ERROR]: No UP interface with private IP found (excluding docker)."
  exit 1
fi

# receiver specific -> configure smcroute
if [ "$ROLE" == "receiver" ]; then
  echo "[INFO] Configuring smcroute for interface: $IFACE"
  echo "phyint $IFACE enable igmp" > /etc/smcroute.conf
fi

echo "[DONE] Installation complete."
