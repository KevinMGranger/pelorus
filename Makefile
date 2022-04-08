# Variable setup and preflight checks

# may override with environment variable
PYTHON_BINARY?=python3

ifndef PELORUS_VENV
  PELORUS_VENV=.venv
endif

ifeq (, $(shell which $(PYTHON_BINARY) ))
  $(error "PYTHON=$(PYTHON_BINARY) binary not found in $(PATH)")
endif

SYS_PYTHON_VER=$(shell $(PYTHON_BINARY) -c 'from sys import version_info; \
  print("%d.%d" % version_info[0:2])')
$(info Found system python version: $(SYS_PYTHON_VER));
PYTHON_VER_CHECK=$(shell $(PYTHON_BINARY) scripts/python-version-check.py)

ifneq ($(strip $(PYTHON_VER_CHECK)),)
  $(error $(PYTHON_VER_CHECK). You may set the PYTHON_BINARY env var to specify a compatible version)
endif

CHART_TEST=$(shell which ct)

SHELLCHECK=$(shell which shellcheck)
SHELL_SCRIPTS=./scripts/pre-commit ./scripts/setup-pre-commit-hook ./demo/demo-tekton

.PHONY: help
# tabs below are required for lines starting in @
help:
	@printf "%-20s %s\n" "Target" "Description"
	@printf "%-20s %s\n" "------" "-----------"
	@make -pqR : 2>/dev/null \
        | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' \
        | sort \
        | egrep -v -e '^[^[:alnum:]]' -e '^$@$$' \
        | xargs -I _ sh -c 'printf "%-20s " _; make _ -nB | (grep -i "^# Help:" || echo "") | tail -1 | sed "s/^# Help: //g"'

.PHONY: default
default: \
  dev-env

.PHONY: all
all: default


# Environment setup

$(PELORUS_VENV): exporters/requirements.txt exporters/requirements-dev.txt
	test -d ${PELORUS_VENV} || ${PYTHON_BINARY} -m venv ${PELORUS_VENV}
	. ${PELORUS_VENV}/bin/activate && \
	       pip install -U pip && \
	       pip install -r exporters/requirements.txt \
	                   -r exporters/requirements-dev.txt
	touch ${PELORUS_VENV}

.PHONY: exporters
exporters: $(PELORUS_VENV)
	. ${PELORUS_VENV}/bin/activate && \
	       pip install -e exporters/

.PHONY: git-blame
git-blame:
	@echo "⎇ Configuring git to ignore certain revs for annotations"
	$(eval IGNORE_REVS_FILE = $(shell git config blame.ignoreRevsFile))
	if [ "$(IGNORE_REVS_FILE)" != ".git-blame-ignore-revs" ]; then \
		git config blame.ignoreRevsFile .git-blame-ignore-revs; \
	fi

.git/hooks/pre-commit: scripts/pre-commit
	./scripts/setup-pre-commit-hook

.PHONY: cli_dev_tools
cli_dev_tools:
	./scripts/install_dev_tools -v $(PELORUS_VENV)

dev-env: $(PELORUS_VENV) cli_dev_tools exporters git-blame \
         .git/hooks/pre-commit
	$(info **** To run VENV: $$source ${PELORUS_VENV}/bin/activate)
	$(info **** To later deactivate VENV: $$deactivate)
	@# Help: dev-env: The default action,  will setup your python development environment

# Release

.PHONY: release minor-release major-release

release:
	./scripts/create_release_pr

minor-release:
	./scripts/create_release_pr -i

major-release:
	./scripts/create_release_pr -m

# Formatting

.PHONY: format black isort format-check black-check isort-check
format: $(PELORUS_VENV) black isort

format-check: $(PELORUS_VENV) black-check isort-check

black: $(PELORUS_VENV)
	. ${PELORUS_VENV}/bin/activate && \
	black exporters scripts

black-check: $(PELORUS_VENV)
	@# Help: Execute black, a python syntax linting tool
	. ${PELORUS_VENV}/bin/activate && \
	black --check exporters scripts

isort: $(PELORUS_VENV)
	. ${PELORUS_VENV}/bin/activate && \
	isort exporters scripts

isort-check: $(PELORUS_VENV)
	. ${PELORUS_VENV}/bin/activate && \
	isort --check exporters scripts


# Linting

.PHONY: lint pylava chart-lint chart-lint-optional shellcheck shellcheck-optional
lint: pylava chart-lint-optional shellcheck-optional

pylava: $(PELORUS_VENV)
	@echo 🐍 🌋 Linting with pylava
	. ${PELORUS_VENV}/bin/activate && \
	pylava

# chart-lint allows us to fail properly when run from CI,
# while chart-lint-optional allows graceful degrading when
# devs don't have it installed.

# shellcheck follows a similar pattern, but is not currently set up for CI.

chart-lint: $(PELORUS_VENV)
	./scripts/install_dev_tools -v $(PELORUS_VENV) -c ct && \
	. ${PELORUS_VENV}/bin/activate && \
	ct lint --config ct.yaml

ifneq (, $(CHART_TEST))
chart-lint-optional: chart-lint
else
chart-lint-optional:
	$(warning chart test (ct) not installed, skipping)
endif

shellcheck:
	@# Help: check for spelling errors
	@echo "🐚 📋 Linting shell scripts with shellcheck"
	$(SHELLCHECK) $(SHELL_SCRIPTS)

ifneq (, $(SHELLCHECK))
shellcheck-optional: shellcheck
else
shellcheck-optional:
	$(warning 🐚 ⏭ Shellcheck not found, skipping)
endif


# Cleanup

clean-dev-env:
	rm -rf ${PELORUS_VENV}
	find . -iname "*.pyc" -delete
