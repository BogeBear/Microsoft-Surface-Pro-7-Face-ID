# SPDX-License-Identifier: GPL-3.0-or-later
CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra -Werror

.PHONY: all offline-tests vm-tests clean
all: build/pam_sp7_research.so build/pam_trace.so build/pam_driver

build:
	mkdir -p build
build/pam_sp7_research.so: src/pam_sp7_research.c | build
	$(CC) $(CFLAGS) -std=c11 -fPIC -shared $< -o $@ -lpam
build/pam_trace.so: tests/pam_trace.c | build
	$(CC) $(CFLAGS) -std=c11 -fPIC -shared $< -o $@ -lpam
build/pam_driver: tests/pam_driver.c | build
	$(CC) $(CFLAGS) -std=c11 $< -o $@ -lpam
offline-tests:
	@test "$$(id -u)" -ne 0 || { echo "Run offline tests as an ordinary user." >&2; exit 2; }
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests python3 -m unittest test_attempt test_pam_layout test_diagnostic_ipc -v
# Run root validation only inside an isolated disposable Linux VM. No install
# target exists; these fixtures never become system PAM configuration.
vm-tests: all
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests SP7_PAM_TEST_BASE=$(CURDIR)/build python3 -m unittest test_attempt test_pam_layout test_pam_flow test_diagnostic_ipc -v
clean:
	rm -f build/pam_sp7_research.so build/pam_trace.so build/pam_driver
