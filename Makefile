# Too Young for Medicare: build pipeline
# Usage: make all | make data | make estimates | make model | make figures | make app

PY := $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
RSCRIPT ?= Rscript

RAW_MEPS := data/raw/meps/h256dta.zip
RAW_NHIS := $(foreach y,21 22 23 24,data/raw/nhis/adult$(y)csv.zip)

.PHONY: all data estimates model figures app

all: data estimates model figures

# Check the raw public-use downloads are in place (see README "Getting the data")
data:
	@missing=0; for f in $(RAW_MEPS) $(RAW_NHIS); do \
	  if [ ! -f $$f ]; then echo "MISSING: $$f"; missing=1; fi; done; \
	  if [ $$missing -eq 1 ]; then echo "Download the files listed in README.md > Getting the data"; exit 1; fi
	@mkdir -p data/interim data/processed
	@echo "Raw data present."

# Survey-weighted estimates (R): MEPS then NHIS
estimates: data
	$(RSCRIPT) R/01_meps_clean.R
	$(RSCRIPT) R/02_meps_estimates.R
	$(RSCRIPT) R/03_meps_models.R
	$(RSCRIPT) R/04_nhis_clean.R
	$(RSCRIPT) R/05_nhis_estimates.R

# Risk model: train on NHIS, validate externally on MEPS
model:
	$(PY) python/train_model.py
	$(PY) python/evaluate_external.py

# Static figure export (for slides)
figures:
	$(PY) app/components/export_figures.py

app:
	$(PY) -m streamlit run app/Home.py
