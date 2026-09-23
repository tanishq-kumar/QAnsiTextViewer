#!/bin/bash -eu
# Build the ClusterFuzzLite fuzzers: install the package (with its Qt
# dependency) plus the fuzzing toolchain, then bundle each *_fuzzer.py
# target into a standalone binary with an execution wrapper, following
# https://google.github.io/clusterfuzzlite/build-integration/python-lang/
python3 -m pip install --upgrade pip
python3 -m pip install atheris pyinstaller
python3 -m pip install .

for fuzzer in $(find "$SRC" -name '*_fuzzer.py'); do
  fuzzer_basename=$(basename -s .py "$fuzzer")
  fuzzer_package=${fuzzer_basename}.pkg
  pyinstaller --distpath "$OUT" --onefile --name "$fuzzer_package" "$fuzzer"
  # Pure-Python target: no LD_PRELOAD of the sanitizer runtime (that is only
  # for native extensions and crashes pure-Python startups). The marker
  # comment is what the runner uses for fuzzer detection.
  echo "#!/bin/sh
# LLVMFuzzerTestOneInput for fuzzer detection.
this_dir=\$(dirname \"\$0\")
\$this_dir/$fuzzer_package \$@" > "$OUT/$fuzzer_basename"
  chmod +x "$OUT/$fuzzer_basename"
done
