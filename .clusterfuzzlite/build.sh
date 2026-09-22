#!/bin/bash -eu
# Build the ClusterFuzzLite fuzzers: install the package (with its Qt
# dependency) plus atheris, then stage the fuzz target.
python3 -m pip install atheris
python3 -m pip install .
cp fuzz/fuzz_ansi.py "$OUT/"
