#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
services="$(docker compose config --services)"
for required in postgres minio minio-init ollama ollama-init trans-api pdf-extractor trans-flow document-builder frontend gateway; do
  grep -qx "$required" <<<"$services" || {
    echo "missing compose service: $required" >&2
    exit 1
  }
done

published="$(docker compose config --format json | python3 -c '
import json, sys
data = json.load(sys.stdin)
for name, service in data["services"].items():
    if service.get("ports"):
        print(name)
')"
test "$published" = "gateway" || {
  echo "only gateway may publish ports; got: $published" >&2
  exit 1
}

docker compose config --quiet
echo "compose contract OK"
