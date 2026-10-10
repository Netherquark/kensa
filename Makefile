SHELL := /bin/bash
COMPOSE := docker compose
.PHONY: build download audit etl spark plots ml all test clean pig-export pig-build pig-run guardrails help

help:
	@echo 'Targets: build download audit etl spark plots ml all test clean pig-build pig-export pig-run guardrails'
	@echo 'Run on Linux with Docker Engine + Compose v2.'

build:
	$(COMPOSE) build ca3

download:
	$(COMPOSE) run --rm ca3 download

audit:
	$(COMPOSE) run --rm ca3 audit

etl:
	$(COMPOSE) run --rm ca3 etl

spark:
	$(COMPOSE) run --rm ca3 spark

plots:
	$(COMPOSE) run --rm ca3 plots

ml:
	$(COMPOSE) run --rm ca3 ml

all:
	$(COMPOSE) run --rm ca3 all

test:
	$(COMPOSE) run --rm ca3 test

pig-build:
	$(COMPOSE) --profile pig build pig

pig-export:
	$(COMPOSE) run --rm ca3 pig-export

pig-run: pig-build pig-export
	$(COMPOSE) --profile pig run --rm pig /opt/pig/bin/pig -x local -param DATA=/workspace/outputs/pig/events.tsv -param OUT=/workspace/outputs/pig/pig_jet_summary pig/analyze_events.pig

clean:
	rm -rf outputs/* data/processed/* audit/*


# Run writingguardrail27 checks against the draft report; requires only Python stdlib.
guardrails:
	python3 quality/guardrail27_check.py
