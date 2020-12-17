#!/usr/bin/env bash
# run misc/build.sh from project root
set -e
set -x

docker image build -t chronicles:latest .
version="$(docker run --rm chronicles:latest /app/chronicles version | awk '{print $NF}')"
docker create --name dummy chronicles:latest
docker cp dummy:/app/chronicles ./chronicles-linux-"${version}"
docker rm -f dummy
