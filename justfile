import 'scripts/just/fleet.just'

# --- Dashboard ---

default:
    @just --list

# --- Quality ---

# Execute Ruff SOTA v13.1 linting
lint:
    cd "{{justfile_directory()}}" && uv run ruff check .
    cd "{{justfile_directory()}}/web_sota" && npx @biomejs/biome ci .

# Execute Ruff SOTA v13.1 fix and formatting
fix:
    cd "{{justfile_directory()}}" && uv run ruff check . --fix --unsafe-fixes && uv run ruff format .
    cd "{{justfile_directory()}}/web_sota" && npx @biomejs/biome check --write .

# --- Serve / Test / Format ---

# Start the HTTP bridge (backend on 10875)
serve:
    uv run python -m handbrake_mcp.server --http --port 10875

# Run the test suite
test:
    uv run pytest tests/ -q

# Format only (no lint)
fmt:
    uv run ruff format .

# MCPB packing comes from scripts/just/fleet.just (mcpb-pack). Do not redefine it here:
# just rejects duplicate recipes, and the fleet shim is the canonical scripts/mcpb-pack.ps1 path.

# --- Hardening ---

# Execute Bandit security audit
check-sec:
    cd "{{justfile_directory()}}" && uv run bandit -r src/

# Execute safety audit of dependencies
audit-deps:
    cd "{{justfile_directory()}}" && uv run safety check

# --- Tauri NSIS ---

# Build the Tauri NSIS desktop installer (Windows-only tooling)
build-native:
	$env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"; $vcvars = "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"; $envOutput = cmd /c "`"$vcvars`" > nul & set" | Where-Object { $_ -match '^(INCLUDE|LIB|LIBPATH|VCToolsVersion|WindowsSdkDir|UniversalCRTSdkDir|UCRTVersion)=' }; foreach ($line in $envOutput) { $parts = $line.Split('=', 2); Set-Item -Path "env:$($parts[0])" -Value $parts[1] -ErrorAction SilentlyContinue }; Set-Location '{{justfile_directory()}}\native'; pwsh -NoProfile -File '{{justfile_directory()}}\native\build.ps1'


# Bootstrap: install dev deps + pre-commit hook
bootstrap:
    uv sync --group dev
    uv run pre-commit install
    echo "Pre-commit hooks installed."
