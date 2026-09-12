#!/usr/bin/env sh
# Packs docker-compose.yml + template.toml the way Dokploy's "Import Template" expects:
# base64 of JSON {"compose": "...", "config": "<template.toml>"}. Output: template.b64.
set -eu
cd "$(dirname "$0")"
python3 - <<'PY'
import base64, json
payload = json.dumps({"compose": open("docker-compose.yml").read(), "config": open("template.toml").read()})
open("template.b64", "w").write(base64.b64encode(payload.encode()).decode() + "\n")
print("wrote template.b64")
PY
