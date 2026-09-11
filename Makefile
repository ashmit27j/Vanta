# Top-level convenience targets. Most of these assume `purplelab` is
# installed (see tooling/README.md: `pip install -e tooling/[dev]` or
# `pipx install -e tooling/`) and that provision/siem/'s own Makefile exists
# -- it's added when Prompt 2 is actually run inside siem-vm (see
# docs/prompt-chain.md); until then, lab-up/lab-down will just fail with a
# clear SSH/remote-Makefile error, which is expected pre-VM-build.

SIEM_HOST ?=
SIEM_USER ?=

.PHONY: lab-up lab-down lab-status daily test coverage

lab-up:
	@if [ -z "$(SIEM_HOST)" ] || [ -z "$(SIEM_USER)" ]; then \
		echo "Set SIEM_HOST and SIEM_USER, e.g. make lab-up SIEM_HOST=192.168.110.10 SIEM_USER=ubuntu"; \
		exit 1; \
	fi
	ssh $(SIEM_USER)@$(SIEM_HOST) 'cd Vanta && make siem-up'

lab-down:
	@if [ -z "$(SIEM_HOST)" ] || [ -z "$(SIEM_USER)" ]; then \
		echo "Set SIEM_HOST and SIEM_USER, e.g. make lab-down SIEM_HOST=192.168.110.10 SIEM_USER=ubuntu"; \
		exit 1; \
	fi
	ssh $(SIEM_USER)@$(SIEM_HOST) 'cd Vanta && make siem-down'

lab-status:
	@if [ -z "$(SIEM_HOST)" ] || [ -z "$(SIEM_USER)" ]; then \
		echo "Set SIEM_HOST and SIEM_USER, e.g. make lab-status SIEM_HOST=192.168.110.10 SIEM_USER=ubuntu"; \
		exit 1; \
	fi
	ssh $(SIEM_USER)@$(SIEM_HOST) 'cd Vanta && make siem-status'

daily:
	purplelab today

test:
	cd tooling && pytest -q

coverage:
	purplelab coverage
