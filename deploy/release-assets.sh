#!/usr/bin/env sh
set -eu

[ $# -eq 3 ] || { echo "usage: release-assets.sh API_VERSION WEB_VERSION OUT_DIR" >&2; exit 1; }
API_VERSION="$1"; WEB_VERSION="$2"; OUT="$3"
IMAGES="${AP_IMAGE_PREFIX:-actionplatformio/action-platform}"
REF="api/v$API_VERSION"

pin() {
  awk -v format="$1" \
    -v api="$IMAGES-api:$API_VERSION" -v worker="$IMAGES-worker:$API_VERSION" -v web="$IMAGES-web:$WEB_VERSION" '
    BEGIN { value["AP_IMAGE_API"] = api; value["AP_IMAGE_WORKER"] = worker; value["AP_IMAGE_WEB"] = web; n = split("AP_IMAGE_API AP_IMAGE_WORKER AP_IMAGE_WEB", keys, " ") }
    {
      for (i = 1; i <= n; i++) {
        if ($0 ~ "^" keys[i] "[ ]*=") { printf format, keys[i], value[keys[i]]; seen[keys[i]] = 1; next }
      }
      print
    }
    END { for (i = 1; i <= n; i++) if (!(keys[i] in seen)) printf format, keys[i], value[keys[i]] }'
}

mkdir -p "$OUT"
git show "$REF:deploy/docker-compose.yml" > "$OUT/docker-compose.yml"
git show "$REF:deploy/dokploy/docker-compose.yml" > "$OUT/docker-compose.dokploy.yml"
git show "$REF:deploy/.env.example" | pin '%s=%s\n' > "$OUT/env.example"
git show "$REF:deploy/dokploy/template.toml" | pin '%s = "%s"\n' > "$OUT/template.toml"
python3 - "$OUT" <<'PY'
import base64, json, pathlib, sys
out = pathlib.Path(sys.argv[1])
payload = json.dumps({"compose": (out / "docker-compose.dokploy.yml").read_text(), "config": (out / "template.toml").read_text()})
(out / "dokploy-template.b64").write_text(base64.b64encode(payload.encode()).decode() + "\n")
PY
rm "$OUT/template.toml"
echo "api $API_VERSION, web $WEB_VERSION → $OUT"
