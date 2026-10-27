# HandBrake MCP Server

<p align="center">
  <a href="https://github.com/casey/just"><img src="https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white" alt="Just"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/PrefectHQ/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.2-7c5cfc?style=flat-square" alt="FastMCP"></a>
</p>


> 📖 **[Installation Guide](INSTALL.md)** — quick start, manual setup, and troubleshooting
>
> 🆕 **First time? Start with [Onboarding](docs/ONBOARDING.md)** — install HandBrakeCLI (the transcoding engine, ~15 MB) before expecting live encodes.

[![CI/CD Pipeline](https://github.com/sandraschi/handbrake-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/sandraschi/handbrake-mcp/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Ready-blue)](https://kubernetes.io/)
[![Security](https://img.shields.io/badge/Security-Enabled-red)](SECURITY.md)
[![Community](https://img.shields.io/badge/Community-Active-blueviolet)](https://github.com/sandraschi/handbrake-mcp/discussions)

A **production-ready**, **FastMCP 3.2.0-compliant** server for professional video transcoding using HandBrakeCLI. Features an **Industrial SOTA Dashboard (v13.1)**, enterprise-grade CI/CD, and robust 127.0.0.1 networking for maximum stability.

## Quick Start

```powershell
git clone https://github.com/sandraschi/handbrake-mcp
cd handbrake-mcp
just
```

This opens an interactive dashboard showing all available commands. Run `just bootstrap` to install dependencies, then `just serve` or `just dev` to start.

### Manual Setup

If you don't have `just` installed:

##  Features

###  **Core Video Processing**
- ** Professional Transcoding**: Convert between all major video formats (MP4, MKV, AVI, MOV, M4V, etc.)
- ** Batch Processing**: Process multiple files simultaneously with intelligent queue management
- ** Watch Folders**: Automatic processing of new video files with configurable patterns
- ** Real-time Progress**: Live job status updates with detailed progress tracking
- ** Quality Presets**: 50+ optimized HandBrake presets for different use cases
- ** Custom Options**: Fine-tune encoding with advanced HandBrake CLI parameters

###  **Enterprise Infrastructure**
- ** CI/CD Pipeline**: Automated testing, building, and deployment across multiple platforms
- ** Real CLI Integration Testing**: Comprehensive testing with actual HandBrakeCLI calls
- ** Docker Support**: Multi-stage builds with security scanning and monitoring
- ** Kubernetes Ready**: Complete deployment manifests for scalable production use
- ** Monitoring**: Prometheus metrics, Grafana dashboards, and health checks
- ** Security**: Vulnerability scanning, SBOM generation, and security  practices
- ** Professional Documentation**: MkDocs with GitHub Pages deployment and versioned docs
- ** Automated Releases**: Changelog generation, release validation, and community notifications

###  **Advanced Documentation System**
- ** Multiline Decorators**: Self-documenting tools with comprehensive metadata
- ** Multilevel Help**: Basic, detailed, and full documentation levels
- ** Advanced Help**: Troubleshooting, examples, and performance optimization guides
- ** Tool Search**: Find tools by name, description, or category
- ** System Status**: Real-time system health and resource monitoring

###  **MCP 2.12.0 Compliance**
- ** 7 Core Tools**: `transcode_video`, `batch_transcode`, `get_job_status`, `cancel_job`, `get_presets`, `get_loaded_models`, `get_provider_status`
- ** 5 Help Tools**: `help`, `multilevel_help`, `advanced_help`, `tool_categories`, `system_status`
- ** Rich Documentation**: Every tool includes detailed descriptions, examples, and usage notes
- ** Cross-references**: Related tools and workflows for enhanced discoverability

###  **Modern GitHub Features**
- ** GitHub Discussions**: Community Q&A and feature discussions
- ** GitHub Wiki**: Comprehensive documentation and troubleshooting guides
- ** Issue/PR Templates**: Professional bug reports and feature requests
- ** Community Health**: Automated stale issue management and metrics
- ** Security Policy**: Responsible disclosure and vulnerability reporting
- ** Contributing Guide**: Clear development and contribution guidelines
- ** Repository Profile**: Enhanced project showcase and discoverability

## Changes in this fork

This fork runs **natively on Linux** — upstream is Windows-first. Branch `local` implements full Linux compatibility (commit `01e6355`):

### Engine discovery & platform layer
- **Platform-aware CLI discovery**: `winget_hbb_path` → `hbb_fallback_paths` — winget links dir on Windows; `/usr/bin/HandBrakeCLI`, `/usr/local/bin`, `/opt/handbrake` on Linux. Overridable via `HBB_FALLBACK_PATHS=a,b,c`.
- **GUI probes cover distro paths** (`/usr/bin/handbrake[-gtk]`), so the classic "GUI installed, engine missing" trap is flagged on Linux too.
- **Platform-aware install hints** (`cli_install_hint()`): winget guidance on Windows, `apt`/`dnf`/`pacman` guidance on Linux in errors and `/health`.
- **POSIX path rules**: the `C:\` drive-letter colon rule is now Windows-only, so Linux filenames like `clip:2024.mp4` are legal.

### HTTP/app layer
- `/api/browse` dashboard picker lists POSIX mount roots (`/`, `/home`, `/mnt`, home) instead of scanning `A:\`–`Z:\`.
- `/api/v1/diagnostics` reports `platform`/`linux`; FastMCP instructions state Windows **and** Linux.
- Legacy `/api/fleet/launch` launches `start.sh` via `/bin/sh` on POSIX (previously crashed with `powershell.exe`/`CREATE_NEW_CONSOLE`); fleet root configurable via `FLEET_REPOS_ROOT`.

### Packaging & tooling
- **pyproject**: dropped the unused `pywin32` dev dependency (it blocked `uv` resolution on Linux); added `Operating System :: POSIX :: Linux` classifier.
- **justfile**: portable `cd … && …` recipes (no forced PowerShell shell); removed the local `mcpb-pack` recipe, which duplicated the one imported from `scripts/just/fleet.just` — just rejects duplicate recipes, so every `just` invocation failed. The fleet shim (`scripts/mcpb-pack.ps1`) remains available.
- `.env.example` and `docs/ONBOARDING.md` updated with Linux install commands; the shell-restart pitfall is now labelled Windows-only.

### Bonus fixes (pre-existing, only visible running natively on Linux)
- `_extract_progress` expected a wrong JSON nesting level; real HandBrakeCLI emits `Progress: { "Working": { "Progress": x } }` — parser fixed (double `@staticmethod` removed, invalid-JSON test transcript corrected).
- Version parsing choked on Arch/git build ids (`HandBrake 20260607133641-…-makepkg`); now scans all lines and accepts both semver and build identifiers.

### Verified on this Linux box
- **Full test suite green: 24 passed**, including real `HandBrakeCLI` integration tests with actual encodes.
- `/health` reports `cli_available: true, cli_path: /usr/bin/HandBrakeCLI, instance_configured: true`.
- `POST /api/transcode` → real encode completes at `progress: 100.0`; stdio entry (`uv run handbrake-mcp-stdio`) starts cleanly.
- All changed files are ruff-clean.

### Repo compliance (standards checker, run manually on Linux)
- `CONTRIBUTING.md` moved to the repo root (the checker only accepts a root-level guide; GitHub renders either location).
- Dropped tracked junk: `error.txt`/`output.txt` (captured run logs) and the `.coverage` artifact (now untracked; it was committed despite being in `.gitignore`).
- `run_server.py` stays at the root on purpose — `scripts/mcpb-pack.ps1` and the PyInstaller build use it as the frozen entry point, so the checker's "move to scripts/" heuristic does not apply.
- Not changed (upstream design, would require inventing content): `assets/icon.svg`, `assets/prompts/system.md`, `requirements.txt`, `release.yml`.

##  Quick Start

### Prerequisites

- **Python 3.8+** - Required for core functionality
- **HandBrakeCLI** - Professional video transcoding engine
- **Git** - For cloning the repository
- **(Optional) MCPB CLI** - For packaging distribution bundles
- **(Optional) Docker** - For containerized deployment
- **(Optional) Kubernetes** - For production deployment

### Installing HandBrakeCLI

#### Windows
```powershell
# Using Windows Package Manager (recommended)
winget install HandBrake.HandBrake.CLI

# Verify installation
HandBrakeCLI --version
```

#### macOS
```bash
# Using Homebrew
brew install handbrake

# Verify installation
HandBrakeCLI --version
```

#### Linux (Ubuntu/Debian)
```bash
# Add HandBrake PPA
sudo add-apt-repository ppa:stebbins/handbrake-releases
sudo apt update
sudo apt install handbrake-cli

# Verify installation
HandBrakeCLI --version
```

## 🚀 Installation & Setup

### 1. Prerequisites
- **Python 3.12+** - Core runtime (managed via `uv` recommended).
- **HandBrakeCLI** - Transcoding engine.
- **[uv](https://docs.astral.sh/uv/)** - Modern Python package and tool manager.

### 2. Quick Deployment
You can run the server directly without manual installation using `uvx`:
```powershell
uvx handbrake-mcp-stdio
```

### 3. Claude Desktop Integration
Add the following to your `claude_desktop_config.json`:
```json
"handbrake-mcp": {
  "command": "uv",
  "args": [
    "--directory", 
    "D:/Dev/repos/handbrake-mcp", 
    "run", 
    "handbrake-mcp-stdio"
  ]
}
```

## 📊 Industrial Dashboard (v13.1)
The project includes a premium, SOTA-compliant dashboard for real-time transcoding management.

### Starting the Dashboard
```powershell
cd web_sota
.\start.bat
```
Visit `http://localhost:51595` to access the control plane.

## 📦 Packaging & Distribution
This repository is SOTA 2026 compliant and uses the officially validated `@anthropic-ai/mcpb` workflow for distribution.

```powershell
# Generate a .mcpb distribution bundle
mcpb pack . dist/handbrake-mcp.mcpb
```

### Prerequisites
- [uv](https://docs.astral.sh/uv/) installed (RECOMMENDED)
- Python 3.12+

## 🛠️ Usage

### **Start the Server**

#### FastMCP stdio (Default for Claude)
```powershell
uv run python -m handbrake_mcp.server
```

#### FastAPI Service (For Dashboard)
```powershell
uv run python -m handbrake_mcp.server --http
```

###  **Discover Available Tools**

The server includes a comprehensive self-documentation system:

```python
# Get basic help for all tools
multilevel_help("basic")

# Get detailed help for specific tools
help("transcode_video", "detailed")

# Get comprehensive documentation
multilevel_help("full")

# Search for tools by functionality
search_tools("video")
search_tools("batch")

# Browse tools by category
tool_categories()
```

###  **Industrial Dashboard**

The server includes a premium, SOTA-v13.1 compliant dashboard in `web_sota`. To run it:

```bash
cd web_sota
npm install
npm run dev
```

> [!IMPORTANT]
> **Windows Networking**: If you encounter "Connection Refused" errors, ensure the dashboard is configured to connect to `127.0.0.1` rather than `localhost`. Modern Windows systems resolve `localhost` to IPv6 `::1`, which may bypass the backend IPv4 listeners.

###  **Core MCP Tools**

#### **Video Processing**
- **`transcode_video`** - Single file transcoding with professional quality settings
- **`batch_transcode`** - Multi-file batch processing with parallel execution

#### **Job Management**
- **`get_job_status`** - Real-time progress monitoring with detailed status
- **`cancel_job`** - Immediate job termination with resource cleanup

#### **Configuration & Discovery**
- **`get_presets`** - List all available HandBrake presets
- **`get_loaded_models`** - MCP-compatible model discovery
- **`get_provider_status`** - Comprehensive system health and capabilities

#### **Help & Documentation**
- **`help`** - Tool-specific help at different detail levels
- **`multilevel_help`** - System-wide help (basic, detailed, full, categories)
- **`advanced_help`** - Advanced guides (examples, troubleshooting, performance)
- **`tool_categories`** - Browse tools by functional category
- **`system_status`** - Real-time system health and resource monitoring

###  **Usage Examples**

#### **Basic Video Transcoding**
```python
# Simple conversion with default settings
result = transcode_video("/videos/input.mp4", "/videos/output.mkv")

# High-quality conversion with custom preset
result = transcode_video(
    "/videos/movie.mkv",
    "/videos/movie_hq.mp4",
    preset="HQ 1080p30"
)

# Custom encoding options
result = transcode_video(
    "/videos/input.avi",
    "/videos/output.mp4",
    options={"quality": "20", "encoder": "x264"}
)
```

#### **Batch Processing**
```python
# Process multiple files
results = batch_transcode([
    {
        "input_path": "/videos/movie1.mp4",
        "output_path": "/videos/movie1.mkv",
        "preset": "Fast 1080p30"
    },
    {
        "input_path": "/videos/movie2.mp4",
        "output_path": "/videos/movie2.mp4"
    }
])

# Check progress of batch jobs
for result in results:
    status = get_job_status(result.job_id)
    print(f"Job {result.job_id}: {status.status} ({status.progress}%)")
```

#### **Job Monitoring & Control**
```python
# Monitor job progress
job_id = "transcode_2025_01_22_143022"
while True:
    status = get_job_status(job_id)
    if status.status in ["completed", "failed", "cancelled"]:
        print(f"Job finished: {status.status}")
        if status.error:
            print(f"Error: {status.error}")
        break
    print(f"Progress: {status.progress}%")
    time.sleep(5)

# Cancel problematic job
cancel_job("job_12345")
```

#### **System Management**
```python
# Check system health
status = get_provider_status()
print(f"Active jobs: {status['active_jobs']}")
print(f"Available presets: {len(status['supported_presets'])}")

# Get available presets
presets = get_presets()
fast_presets = [p for p in presets if "Fast" in p]
print(f"Fast presets: {fast_presets}")
```

###  **Advanced Documentation Access**

#### **Multilevel Help System**
```python
# Basic overview of all tools
help_overview = multilevel_help("basic")

# Detailed information about specific tools
transcode_help = multilevel_help("detailed", "transcode_video")

# Complete documentation for all tools
full_docs = multilevel_help("full")

# Browse tools by category
categories = multilevel_help("categories")
```

#### **Advanced Help Types**
```python
# Usage examples and  practices
examples = advanced_help("examples")

# Troubleshooting guide
troubleshooting = advanced_help("troubleshooting")

# Performance optimization guide
performance = advanced_help("performance")

# System overview
overview = advanced_help("overview")
```

###  **Self-Documenting Tools**

Every tool includes comprehensive documentation accessible through the help system:

```python
# Get full documentation for any tool
full_doc = help("transcode_video", "full")
print(full_doc)
```

This will show:
- Complete tool description with features
- Parameter documentation with types and examples
- Multiple usage examples (basic, advanced, real-world)
- Return value specifications
- Important notes and warnings
- Related tools and workflows
- Version information

##  Packaging & Distribution

This repository uses the SOTA 2026 packing workflow. See the [Installation](#installation-options) section for details on generating distribution bundles.


## 📖 Documentation & Resources
For detailed technical guides, standards, and advanced usage, please refer to the local documentation hub:
- **[Documentation Index](docs/index.md)**: Your primary entry point for guides and help.
- **[CHANGELOG.md](CHANGELOG.md)**: Track version history and industrialization milestones.

## 🤝 Contributing
Contributions are welcome! Please follow the materialist efficiency standards-based development patterns outlined in our internal documentation.

## 📜 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
**HandBrake MCP | Industrial Transcoding Control Plane | 2026**


## 🛡️ Industrial Quality Stack

This project adheres to **SOTA 14.1** industrial standards for high-fidelity agentic orchestration:

- **Python (Core)**: [Ruff](https://astral.sh/ruff) for linting and formatting. Zero-tolerance for `print` statements in core handlers (`T201`).
- **Webapp (UI)**: [Biome](https://biomejs.dev/) for sub-millisecond linting. Strict `noConsoleLog` enforcement.
- **Protocol Compliance**: Hardened `stdout/stderr` isolation to ensure crash-resistant JSON-RPC communication.
- **Automation**: [Justfile](./justfile) recipes for all fleet operations (`just lint`, `just fix`, `just dev`).
- **Security**: Automated audits via `bandit` and `safety`.
