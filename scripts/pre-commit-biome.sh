#!/bin/sh
# POSIX counterpart of scripts/pre-commit-biome.ps1 (fleet template:
# mcp-central-docs/templates/pre-commit-biome.ps1). Use this one on Linux/macOS hosts;
# the .ps1 form cannot be spawned there (no powershell.exe in PATH).
#
# Detects the web root (webapp/ canonical, then legacy variants), ensures node_modules,
# and runs the biome CI check. Exits 0 when the repository has no web root, so the hook
# is a no-op on Python-only repos.
#
# pre-commit runs hooks with the working directory set to the repository root.

set -u

root=$(pwd)

web_root=""
for candidate in webapp webapp/frontend web_sota web-sota web frontend ui web_app; do
    if [ -f "$root/$candidate/package.json" ]; then
        web_root="$root/$candidate"
        break
    fi
done

if [ -z "$web_root" ]; then
    exit 0
fi

cd "$web_root" || exit 0

if command -v bun >/dev/null 2>&1; then
    runner=bun
else
    runner=npm
fi

if [ ! -d node_modules ]; then
    if [ "$runner" = bun ]; then
        bun install --frozen-lockfile 2>/dev/null || bun install 2>/dev/null
    else
        npm ci --silent || npm install --silent
    fi
fi

"$runner" run biome:ci
