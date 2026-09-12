#!/usr/bin/env bash
# Provisions siem-vm (Ubuntu Server): Docker + the official Wazuh single-node
# Docker stack (indexer + manager + dashboard), with archives enabled so the
# Sigma pipeline (Prompt 6) has more than just Wazuh's own alerts to query.
#
# INetSim (Prompt 3) is provisioned separately by inetsim/install.sh in this
# same directory -- it's a distinct service (a fake-internet sinkhole, not
# part of the Wazuh stack) with its own, much simpler install path.
#
# Idempotent: safe to re-run after a partial failure or on an
# already-provisioned box. Run this INSIDE siem-vm, not on the Windows host.
#
# CAVEAT (read before running): this clones the upstream wazuh-docker repo at
# a pinned tag rather than vendoring a hand-written compose file, because that
# repo's internal structure (cert generation flow, config file paths) changes
# between Wazuh releases and is easy to get subtly wrong from memory. Verify
# the WAZUH_VERSION below is still current, and that the archives sed below
# actually matched something (it warns if not) against the version you clone.

set -euo pipefail

WAZUH_VERSION="${WAZUH_VERSION:-4.9.2}"
WAZUH_DOCKER_DIR="${WAZUH_DOCKER_DIR:-$HOME/wazuh-docker}"

echo "==> Checking Docker"
if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER"
    echo "Docker installed. Log out and back in (or run 'newgrp docker') for group membership to take effect."
fi

echo "==> Checking the OpenSearch-required vm.max_map_count"
current_max_map_count="$(sysctl -n vm.max_map_count)"
if [ "$current_max_map_count" -lt 262144 ]; then
    sudo sysctl -w vm.max_map_count=262144
    grep -q "^vm.max_map_count" /etc/sysctl.conf 2>/dev/null || \
        echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf >/dev/null
fi

echo "==> Fetching wazuh-docker v${WAZUH_VERSION} (pinned)"
if [ ! -d "$WAZUH_DOCKER_DIR" ]; then
    git clone --branch "v${WAZUH_VERSION}" --depth 1 https://github.com/wazuh/wazuh-docker.git "$WAZUH_DOCKER_DIR"
else
    echo "    $WAZUH_DOCKER_DIR already exists -- not re-cloning. Remove it to pull a different version."
fi
cd "$WAZUH_DOCKER_DIR/single-node"

echo "==> Enabling archives (required by the Sigma pipeline -- see detections/README.md)"
manager_conf="config/wazuh_cluster/wazuh_manager.conf"
if [ -f "$manager_conf" ]; then
    if grep -q "<logall>no</logall>" "$manager_conf" 2>/dev/null; then
        sed -i \
            -e 's/<logall>no<\/logall>/<logall>yes<\/logall>/' \
            -e 's/<logall_json>no<\/logall_json>/<logall_json>yes<\/logall_json>/' \
            "$manager_conf"
        echo "    archives enabled in $manager_conf"
    else
        echo "    WARNING: could not confirm '<logall>no</logall>' in $manager_conf -- verify archives"
        echo "    are enabled (<logall>yes</logall> and <logall_json>yes</logall_json>) by hand before"
        echo "    relying on the Sigma pipeline. This script's sed pattern may not match this Wazuh version."
    fi
else
    echo "    WARNING: $manager_conf not found -- enable archives by hand (see detections/README.md)."
fi

echo "==> Generating indexer TLS certs (skipped if already present)"
if [ ! -d "config/wazuh_indexer_ssl_certs" ] || [ -z "$(ls -A config/wazuh_indexer_ssl_certs 2>/dev/null)" ]; then
    docker compose -f generate-indexer-certs.yml run --rm generator
else
    echo "    certs already present -- not regenerating."
fi

echo "==> Bringing the stack up"
docker compose up -d

echo ""
echo "Wazuh dashboard should be reachable shortly at: https://$(hostname -I | awk '{print $1}')/"
echo "Default credentials live in $WAZUH_DOCKER_DIR/single-node/config -- CHANGE THEM before this box"
echo "sees real use, even in an isolated lab. See provision/siem/README.md for details."
echo ""
echo "Next: run inetsim/install.sh in this directory to bring up the detonation sinkhole (Prompt 3)."
