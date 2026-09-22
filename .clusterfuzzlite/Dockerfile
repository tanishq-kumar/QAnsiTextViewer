FROM gcr.io/oss-fuzz-base/base-builder-python:v1
RUN python3 -m pip install --upgrade pip
COPY . $SRC/QAnsiTextViewer
WORKDIR $SRC/QAnsiTextViewer
COPY .clusterfuzzlite/build.sh $SRC/build.sh
