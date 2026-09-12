# Run on siem-vm, after provision/siem/install.sh has cloned wazuh-docker.
# See install.sh for how WAZUH_DOCKER_DIR is chosen. INetSim runs as a
# systemd service (see inetsim/install.sh), not docker compose.

WAZUH_DOCKER_DIR ?= $(HOME)/wazuh-docker
COMPOSE = docker compose -f $(WAZUH_DOCKER_DIR)/single-node/docker-compose.yml

.PHONY: siem-up siem-down siem-logs siem-status

siem-up:
	bash install.sh
	bash inetsim/install.sh

siem-down:
	$(COMPOSE) down
	sudo systemctl stop inetsim

siem-logs:
	$(COMPOSE) logs -f --tail=200 &
	sudo journalctl -u inetsim -f

siem-status:
	$(COMPOSE) ps
	@echo "---"
	sudo systemctl status inetsim --no-pager
