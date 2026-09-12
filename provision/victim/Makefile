# Run on victim-vm. victim-provision needs SIEM_MANAGER_IP (see install.sh);
# pass it as an env var or a make variable:
#   make victim-provision SIEM_MANAGER_IP=192.168.110.10

SIEM_MANAGER_IP ?=

.PHONY: victim-provision victim-verify

victim-provision:
ifeq ($(strip $(SIEM_MANAGER_IP)),)
	$(error Set SIEM_MANAGER_IP, e.g. make victim-provision SIEM_MANAGER_IP=192.168.110.10)
endif
	SIEM_MANAGER_IP=$(SIEM_MANAGER_IP) bash install.sh

victim-verify:
	@echo "-- Wazuh agent --"
	@systemctl is-active wazuh-agent || echo "NOT RUNNING"
	@echo "-- auditd --"
	@systemctl is-active auditd || echo "NOT RUNNING"
	@sudo auditctl -l | grep -q . && echo "rules loaded" || echo "NO RULES LOADED"
	@echo "-- Sysmon --"
	@systemctl is-active sysmon || echo "NOT RUNNING"
	@echo "-- PowerShell + Invoke-AtomicRedTeam --"
	@command -v pwsh >/dev/null && pwsh -v || echo "pwsh NOT FOUND"
	@test -d "$$HOME/AtomicRedTeam/atomics" && echo "atomics present" || echo "ATOMICS NOT FOUND"
	@echo "-- samples dir --"
	@test -d "$$HOME/samples" && stat -c "%a %n" "$$HOME/samples" || echo "NOT FOUND"
