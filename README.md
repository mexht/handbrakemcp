# HandBrake MCP Server

[![just](https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white)](https://github.com/casey/just)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastMCP](https://img.shields.io/badge/FastMCP-3.2-7c5cfc?style=flat-square)](https://github.com/PrefectHQ/fastmcp)
[![CI](https://github.com/sandraschi/handbrake-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/sandraschi/handbrake-mcp/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue)](https://www.docker.com/)
[![Security](https://img.shields.io/badge/Security-Enabled-red)](SECURITY.md)
[![Discussions](https://img.shields.io/badge/Community-Active-blueviolet)](https://github.com/sandraschi/handbrake-mcp/discussions)

A FastMCP 3.2.0-compliant MCP server for video transcoding with HandBrakeCLI: single and batch
transcodes, live job progress, watch-folder automation, and a browser/Tauri control-plane dashboard.
Runs natively on **Windows and Linux**.

> **[Installation Guide](INSTALL.md)** — setup, configuration, troubleshooting
> **First time?** Start with [Onboarding](docs/ONBOARDING.md) — you need HandBrakeCLI (the
> transcoding engine, ~15 MB) before any encode will run.

## Quick Start

```bash
git clone https://github.com/sandraschi/handbrake-mcp
cd handbrake-mcp
just                 # lists every recipe
just bootstrap       # install dev deps + pre-commit hooks
just serve           # HTTP backend on 127.0.0.1:10875
just test            # pytest suite
```

Without `just`: `uv sync --group dev`, then `uv run pytest tests/ -q` and
`uv run python -m handbrake_mcp.server --http`.

Or run the server with no install at all: `uvx handbrake-mcp-stdio`.

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/), HandBrakeCLI, Git.

### Installing HandBrakeCLI

```powershell
# Windows
winget install HandBrake.HandBrake.CLI
```

```bash
# macOS
brew install handbrake

# Linux (Ubuntu/Debian)
sudo add-apt-repository ppa:stebbins/handbrake-releases
sudo apt update && sudo apt install handbrake-cli

# Arch — HandBrakeCLI ships in extra
sudo pacman -S handbrake-cli
```

Then verify: `HandBrakeCLI --version`.

## Changes in this fork

This fork runs **natively on Linux** — upstream is Windows-first. Branch `local` implements full
Linux compatibility:

### Engine discovery and platform layer

- **Platform-aware CLI discovery**: `winget_hbb_path` replaced by `hbb_fallback_paths` — winget links
  dir on Windows; `/usr/bin/HandBrakeCLI`, `/usr/local/bin`, `/opt/handbrake` on Linux. Override with
  `HBB_FALLBACK_PATHS=a,b,c`.
- **GUI probes cover distro paths** (`/usr/bin/handbrake[-gtk]`), so the "GUI installed, engine
  missing" trap is flagged on Linux too.
- **Platform-aware install hints** (`cli_install_hint()`): winget guidance on Windows,
  `apt`/`dnf`/`pacman` guidance on Linux, used in errors and `/health`.
- **POSIX path rules**: the `C:\` drive-letter colon rule is Windows-only, so names like
  `clip:2024.mp4` are legal on Linux.

### HTTP/app layer

- `/api/browse` dashboard picker lists POSIX mount roots (`/`, `/home`, `/mnt`, home) instead of
  scanning `A:\`–`Z:\`.
- `/api/v1/diagnostics` reports `platform`/`linux`; FastMCP instructions state Windows **and** Linux.
- Legacy `/api/fleet/launch` runs `start.sh` via `/bin/sh` on POSIX (previously crashed through
  `powershell.exe`/`CREATE_NEW_CONSOLE`); fleet root configurable via `FLEET_REPOS_ROOT`.

### Packaging and tooling

- **pyproject**: dropped the unused `pywin32` dev dependency (it blocked `uv` resolution on Linux);
  added the `Operating System :: POSIX :: Linux` classifier.
- **justfile**: portable `cd … && …` recipes (no forced PowerShell shell); removed the local
  `mcpb-pack` recipe that collided with the one imported from `scripts/just/fleet.just` — `just`
  rejects duplicate recipes, which made every `just` invocation fail.
- `.env.example` and `docs/ONBOARDING.md` gained Linux install commands; the shell-restart pitfall is
  labelled Windows-only.

### Fixes found while running natively on Linux

- `_extract_progress` expected the wrong JSON nesting; real HandBrakeCLI emits
  `Progress: { "Working": { "Progress": x } }` (0..1 fraction). Parser corrected.
- Version parsing choked on Arch/git build ids (`HandBrake 20260607133641-…-makepkg`); it now scans
  all lines and accepts both semver and build identifiers.

### Verified on this machine

- Test suite green: **24 passed**, including real `HandBrakeCLI` encodes.
- `/health`: `cli_available: true`, `cli_path: /usr/bin/HandBrakeCLI`, `instance_configured: true`.
- `POST /api/transcode` completes at `progress: 100.0`; `uv run handbrake-mcp-stdio` starts cleanly.
- Changed files are ruff-clean.

### Repo compliance

Standards rules were checked manually (the PowerShell checker cannot run here).

- `CONTRIBUTING.md` moved to the repo root; GitHub renders either location.
- Removed tracked junk: `error.txt`/`output.txt` (captured run logs) and the committed `.coverage`
  artifact (still ignored, now untracked).
- `run_server.py` stays at the root on purpose — `scripts/mcpb-pack.ps1` and the PyInstaller build use
  it as the frozen entry point.
- Left as upstream design (fixing would mean inventing content): `assets/icon.svg`,
  `assets/prompts/system.md`, `requirements.txt`, `release.yml`.

## Running the server

| Entry point | Command | Use |
|---|---|---|
| stdio (MCP client) | `uv run python -m handbrake_mcp.server` | Claude, other MCP clients |
| HTTP backend | `uv run python -m handbrake_mcp.server --http` | dashboard + API, port 10875 |
| packaged entry | `uv run handbrake-mcp-stdio` | same server, console-script form |

Configuration comes from `.env` (all keys are listed in `.env.example`): `HBB_PATH`, `HBB_FALLBACK_PATHS`
(commented), `DEFAULT_PRESET`, `WATCH_FOLDERS`, `PROCESSED_FOLDER`, `DELETE_ORIGINAL_AFTER_PROCESSING`,
`FILE_PATTERNS`, `HOST`/`PORT`, `MCP_TRANSPORT`/`MCP_HOST`/`MCP_PORT`, `LOG_LEVEL`, `API_KEY`,
`WEBHOOK_URL`/`WEBHOOK_EVENTS`, `EMAIL_NOTIFICATIONS`/`EMAIL_RECIPIENTS`/`EMAIL_SENDER`.

Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "handbrake-mcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/handbrake-mcp", "run", "handbrake-mcp-stdio"]
    }
  }
}
```

## Tools

Video and jobs:

- `transcode_video(input_path, output_path, preset?, options?)` — single file
- `batch_transcode(jobs)` — multiple files with queue management
- `get_job_status(job_id)` — status and progress
- `cancel_job(job_id)` — stop a running encode

Discovery and configuration:

- `get_presets()` — HandBrake presets
- `get_provider_status()` — engine availability, capabilities, active jobs
- `get_loaded_models()` — loaded model/encoder information

Self-documentation:

- `help(name, level)`, `multilevel_help(level, filter?)`, `advanced_help(tool?, help_type)`,
  `tool_categories()`, `search_tools(query)`, `system_status()`, `show_status_card()`

## Usage

```python
# Single transcode: preset, or raw encoder options that override it
transcode_video("/videos/input.mp4", "/videos/output.mkv")
transcode_video("/videos/movie.mkv", "/videos/movie_hq.mp4", preset="HQ 1080p30")
transcode_video("/videos/input.avi", "/videos/output.mp4", options={"quality": "20", "encoder": "x264"})

# Batch: each job may carry its own preset/options
results = batch_transcode([
    {"input_path": "/videos/m1.mp4", "output_path": "/videos/m1.mkv", "preset": "Fast 1080p30"},
    {"input_path": "/videos/m2.mp4", "output_path": "/videos/m2.mp4"},
])

# Monitor and control
status = get_job_status("job_12345")   # status: queued|processing|completed|failed|cancelled, progress 0-100
cancel_job("job_12345")

# Config discovery
presets = get_presets()
provider = get_provider_status()       # cli_available, supported_presets, active_jobs

# Docs without leaving the session
help("transcode_video", "detailed")
multilevel_help("categories")
advanced_help(help_type="troubleshooting")   # overview|examples|troubleshooting|performance
advanced_help("transcode_video", "examples") # tool_name first, then help_type
search_tools("batch")
```

Every tool returns a structured dict with `success`, `message`, and domain fields, so failures carry
an actionable `error` instead of a stack trace.

## Dashboard

The control plane lives in `web_sota` (Vite/React). Start the backend first (`just serve`), then:

```bash
cd web_sota
npm install
npm run dev        # http://127.0.0.1:10874
```

Windows also has `web_sota/start.bat` / `start.ps1`. Both bind `127.0.0.1`: on Windows, resolve
`localhost` to IPv4 explicitly — modern Windows maps `localhost` to `::1`, which misses the IPv4
backend listener and yields "Connection refused".

## Packaging

MCPB bundles use the `@anthropic-ai/mcpb` workflow; `manifest.json` declares the entry point, tools,
and user config.

```bash
npx --yes @anthropic-ai/mcpb pack . dist/handbrake-mcp-v1.1.1.mcpb
```

`mcpb-pack` is also available as a `just` recipe via `scripts/just/fleet.just` — that recipe shells
out to PowerShell, so it is Windows-only tooling. Packaging also lives in `Dockerfile`,
`docker-compose.yml`, and the `k8s/` manifests (`deployment`, `service`, `configmap`, `ingress`,
`pvc`); see [INSTALL.md](INSTALL.md).

## Documentation

- [docs/index.md](docs/index.md) — documentation index
- [INSTALL.md](INSTALL.md) — installation and deployment
- [docs/ONBOARDING.md](docs/ONBOARDING.md) — first-time setup, HandBrakeCLI pitfalls
- [CHANGELOG.md](CHANGELOG.md) — history, including this fork's changes
- [CONTRIBUTING.md](CONTRIBUTING.md) — development guide
- [SECURITY.md](SECURITY.md) — disclosure policy

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Keep the FastMCP portmanteau tool
pattern (`operation` enum, structured responses) and run `just lint` / `just fix` before opening a PR.

## License

[MIT](LICENSE)

## Quality stack

- **Python**: [Ruff](https://astral.sh/ruff) lint + format, `T201` blocks `print` in handlers
- **Web UI**: [Biome](https://biomejs.dev/) check + `noConsoleLog`
- **CI**: GitHub Actions ([ci.yml](.github/workflows/ci.yml)), shared fleet workflow
- **Automation**: [`justfile`](justfile) recipes — `lint`, `fix`, `fmt`, `test`, `serve`,
  `check-sec` (bandit), `audit-deps` (safety), `bootstrap`
- **Hooks**: pre-commit (ruff, ruff-fix, ruff-format, whitespace/YAML/large-file guards)
