"""HandBrake service for video transcoding."""

import asyncio
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from handbrake_mcp.core.config import settings

logger = logging.getLogger(__name__)


class HandBrakeError(Exception):
    """Custom exception for HandBrake related errors."""

    pass


def gui_install_paths() -> list[str]:
    """Well-known HandBrake *GUI* install locations (which do NOT ship the CLI).

    Windows: ``Program Files`` layout. Linux: distro package locations — the
    GUI ships as ``handbrake``/``handbrake-gtk``; ``HandBrakeCLI`` is always a
    separate binary (on Debian it even lives in a separate ``handbrake-cli``
    package). Used only to flag the classic GUI-without-engine trap.
    """
    if os.name != "nt":
        return [
            "/usr/bin/handbrake",
            "/usr/bin/handbrake-gtk",
            "/usr/local/bin/handbrake",
        ]

    candidates = [
        r"C:\Program Files\HandBrake\HandBrake.exe",
        r"C:\Program Files (x86)\HandBrake\HandBrake.exe",
    ]
    program_files = os.environ.get("ProgramFiles")
    if program_files and program_files.lower() not in ("c:\\program files",):
        candidates.append(str(Path(program_files) / "HandBrake" / "HandBrake.exe"))
    program_files_x86 = os.environ.get("ProgramFiles(x86)")
    if program_files_x86 and program_files_x86.lower() != r"c:\program files (x86)":
        candidates.append(str(Path(program_files_x86) / "HandBrake" / "HandBrake.exe"))
    return candidates


def cli_install_hint() -> str:
    """Platform-appropriate HandBrakeCLI install guidance for onboarding UX."""
    if os.name == "nt":
        return (
            "install it with 'winget install -e --id HandBrake.HandBrake.CLI', then restart "
            "the terminal so the new PATH entry becomes visible"
        )
    return (
        "install it with your distro package manager (e.g. 'sudo apt install handbrake-cli' on "
        "Debian/Ubuntu, 'sudo dnf install handbrake-cli' on Fedora, 'pacman -S handbrake-cli' on "
        "Arch) — the desktop GUI package alone does not provide HandBrakeCLI — or set HBB_PATH "
        "in your environment to an existing HandBrakeCLI binary"
    )


def probe_handbrake_cli() -> dict[str, Any]:
    """Non-raising HandBrakeCLI presence probe for /health and onboarding UX.

    Checks PATH first, then the platform fallback locations (winget links dir
    on Windows, ``/usr/bin``-style package paths on Linux — see
    ``settings.hbb_fallback_paths``). Also reports whether the HandBrake *GUI*
    is installed — the classic trap is seeing ``HandBrake``/``HandBrake.exe``
    and assuming the engine is there. The GUI never ships HandBrakeCLI on any
    platform. Never raises; the Dashboard red onboarding CTA and the sanity
    check in docs/ONBOARDING.md read this.

    ## Return Format
    `{"available": bool, "path": str | None, "gui_present": bool}`.

    ## Examples
    `probe_handbrake_cli()` → `{"available": True, "path": "/usr/bin/HandBrakeCLI", "gui_present": False}`.
    """
    from handbrake_mcp.core.config import settings as _settings

    found = shutil.which(_settings.hbb_path)
    if not found:
        for fallback in _settings.hbb_fallback_paths:
            if Path(fallback).exists():
                found = fallback
                break
    gui = any(Path(p).exists() for p in gui_install_paths())
    return {"available": found is not None, "path": found, "gui_present": gui}


class TranscodeJob(BaseModel):
    """Model for a transcoding job."""

    model_config = {"arbitrary_types_allowed": True}

    job_id: str
    input_path: Path
    output_path: Path
    preset: str = settings.default_preset
    options: dict[str, str | int | float | bool] = Field(default_factory=dict)
    status: str = "pending"
    progress: float = 0.0
    error: str | None = None
    process: asyncio.subprocess.Process | None = None


class HandBrakeService:
    """Service for handling HandBrake operations."""

    def __init__(self):
        self.handbrake_path = self._find_handbrake()
        self.handbrake_version = None
        self.jobs: dict[str, TranscodeJob] = {}
        self._supported_presets: list[str] = []
        self._max_concurrent_jobs = 5  # Rate limiting
        self._max_file_size_gb = 10  # Maximum file size in GB
        self._min_file_size_bytes = 1024  # Minimum file size in bytes
        self._max_option_value_length = 1000  # Maximum length for option values

    def _find_handbrake(self) -> Path:
        """Find HandBrakeCLI in the system PATH or platform fallback locations."""
        # 1. Check standard PATH/configured path
        handbrake_path = shutil.which(settings.hbb_path)

        # 2. Check platform fallbacks (winget links dir on Windows, distro
        #    package paths on Linux) if standard lookup fails
        if not handbrake_path:
            for fallback in settings.hbb_fallback_paths:
                if Path(fallback).exists():
                    handbrake_path = fallback
                    break
            if not handbrake_path:
                logger.info(
                    f"HandBrakeCLI not in PATH, checked fallback locations: {settings.hbb_fallback_paths}"
                )

        if not handbrake_path:
            raise HandBrakeError(
                f"HandBrakeCLI not found. Checked PATH and {settings.hbb_fallback_paths}. "
                f"{cli_install_hint()} (see docs/ONBOARDING.md § First-timer setup steps), then restart "
                f"your terminal — or set HBB_PATH in your environment variables."
            )
        return Path(handbrake_path)

    async def get_handbrake_version(self) -> str:
        """Get the HandBrake CLI version."""
        if self.handbrake_version is None:
            try:
                result = await self._run_handbrake(["--version"])
                # Version line like "HandBrake 1.11.2 (2023010100)"; Arch/git
                # nightly builds print an identifier instead ("HandBrake 20260607133641-abc-makepkg").
                # Scan all lines: noise like "HandBrake has exited." must not mask it.
                lines = result.strip().split("\n")
                import re

                version_match = None
                for line in lines:
                    version_match = re.search(r"HandBrake\s+(\d[\w.-]*)", line)
                    if version_match:
                        break
                if version_match:
                    self.handbrake_version = version_match.group(1).strip("-")
                else:
                    self.handbrake_version = "unknown"
            except Exception as e:
                logger.error(f"Failed to get HandBrake version: {e}")
                self.handbrake_version = "unknown"
        return self.handbrake_version

    async def get_presets(self) -> list[str]:
        """Get list of available HandBrake presets."""
        if not self._supported_presets:
            try:
                # First get the version to ensure HandBrake is working
                await self.get_handbrake_version()

                # Try to get presets using the modern CLI interface
                result = await self._run_handbrake(["--preset-list"])
                self._supported_presets = self._parse_presets_from_output(result)

                # If that fails, try the older method
                if not self._supported_presets:
                    logger.warning("Modern preset list failed, trying legacy method")
                    result = await self._run_handbrake(["--preset-import-gui", "--preset-import-file", "-"])
                    self._supported_presets = self._parse_presets_from_output(result)

                # If still no presets, use fallback list
                if not self._supported_presets:
                    logger.warning("Using fallback preset list")
                    self._supported_presets = ["Fast 1080p30", "HQ 1080p30 Surround", "Web Optimized"]

            except Exception as e:
                logger.error(f"Failed to get presets: {e}")
                raise HandBrakeError(f"Failed to get presets: {e}")
        return self._supported_presets

    def _parse_presets_from_output(self, output: str) -> list[str]:
        """Parse preset names from HandBrake CLI output.

        HandBrakeCLI >= 1.x prints the list on stderr in this shape::

            General/
                Very Fast 1080p30
                    Small H.264 video (up to 1080p30) ...

        Category headers end with ``/`` at zero indent, preset names sit at
        4-space indent, and their descriptions are indented deeper. Engine log
        lines start with ``[``. (Older mock-style fixtures with 2-space names
        and no categories still parse: any 2-6-space-indented line counts.)
        """
        presets = []
        for raw_line in output.splitlines():
            if not raw_line.strip():
                continue
            stripped = raw_line.strip()
            if stripped.startswith("["):
                continue  # engine log line, e.g. "[10:35:18] hb_init: ..."
            if stripped.startswith("+"):
                continue  # legacy container markers
            if stripped.endswith("/"):
                continue  # category header, e.g. "General/"
            indent = len(raw_line) - len(raw_line.lstrip(" "))
            if 2 <= indent <= 6:
                presets.append(stripped)
            elif indent == 0:
                # Bare non-category line (legacy "Preset (Category)" shape):
                # strip a trailing "(...)" qualifier if present.
                if "(" in stripped:
                    stripped = stripped.split("(")[0].strip()
                if len(stripped) > 2:
                    presets.append(stripped)
            # Deeper indents are description text — skip.

        # Remove duplicates and sort
        presets = list(set(presets))
        presets.sort()

        return presets

    async def transcode(
        self,
        input_path: str | Path,
        output_path: str | Path,
        preset: str | None = None,
        options: dict[str, str | int | float | bool] | None = None,
    ) -> str:
        """Start a transcoding job with rate limiting and validation.

        Args:
            input_path: Path to input video file (validated for security)
            output_path: Path for output file (validated for security)
            preset: HandBrake preset name (validated against available presets)
            options: Additional HandBrake options (sanitized)

        Returns:
            Job ID for tracking progress

        Raises:
            FileNotFoundError: If input file doesn't exist
            ValueError: If preset is invalid or system overloaded
            HandBrakeError: If HandBrake CLI fails
        """
        # Security: Validate and canonicalize paths
        input_path = self._validate_and_secure_path(input_path)
        output_path = self._validate_and_secure_path(output_path)

        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Validate file size (prevent processing extremely large files)
        file_size = input_path.stat().st_size
        max_file_size = self._max_file_size_gb * 1024 * 1024 * 1024
        if file_size > max_file_size:
            raise ValueError(
                f"Input file too large: {file_size / (1024 * 1024 * 1024):.1f}GB (max: {self._max_file_size_gb}GB)"
            )

        if file_size < self._min_file_size_bytes:
            raise ValueError(f"Input file too small: {file_size} bytes (min: {self._min_file_size_bytes} bytes)")

        # Rate limiting: Check concurrent jobs
        running_jobs = len([job for job in self.jobs.values() if job.status == "processing"])
        if running_jobs >= self._max_concurrent_jobs:
            raise ValueError(
                f"Maximum concurrent jobs ({self._max_concurrent_jobs}) reached. Please wait for existing jobs to complete."
            )

        # Check system resources before starting new job
        await self._check_system_resources()

        # Validate preset if provided
        if preset and preset not in await self.get_presets():
            raise ValueError(f"Invalid preset: {preset}")

        # Sanitize options to prevent command injection
        safe_options = self._sanitize_options(options or {})

        job_id = f"job_{len(self.jobs) + 1}_{input_path.stem}"

        job = TranscodeJob(
            job_id=job_id,
            input_path=input_path,
            output_path=output_path,
            preset=preset or settings.default_preset,
            options=safe_options,
            status="queued",
        )

        self.jobs[job_id] = job

        # Start the transcoding task
        asyncio.create_task(self._run_transcode_job(job))

        return job_id

    def _validate_and_secure_path(self, path: str | Path) -> Path:
        """Validate and secure file path to prevent directory traversal attacks."""
        # Convert to string for validation
        path_str = str(path)

        # Security: Prevent dangerous characters (shell metacharacters are rejected
        # on every platform; a colon is additionally constrained to a Windows drive
        # prefix like `C:\`, but on POSIX ':' is an ordinary filename character)
        dangerous_chars = ["<", ">", '"', "|", "?", "*"]
        for char in dangerous_chars:
            if char in path_str:
                raise ValueError(f"Invalid characters in path: {path}")

        if os.name == "nt":
            # Allow single colon for Windows drive letters (e.g., C:\)
            colon_count = path_str.count(":")
            if colon_count > 1:
                raise ValueError(f"Invalid path format: {path}")
            if colon_count == 1 and not (len(path_str) > 1 and path_str[1] == ":"):
                raise ValueError(f"Invalid colon usage in path: {path}")

        # Convert to Path object and resolve
        path_obj = Path(path).resolve()

        # Prevent directory traversal
        if ".." in path_obj.parts:
            raise ValueError(f"Directory traversal detected in path: {path}")

        # Check if path exists (for input files)
        # Note: Output directories may not exist yet, so we don't check for them

        # Validate file extension for input files
        if path_obj.is_file():
            allowed_extensions = {".mp4", ".mkv", ".avi", ".mov", ".m4v", ".wmv", ".flv", ".webm"}
            if path_obj.suffix.lower() not in allowed_extensions:
                raise ValueError(f"Unsupported file format: {path_obj.suffix}")

        # Additional security: Check path length
        if len(str(path_obj)) > 1000:
            raise ValueError(f"Path too long: {path}")

        # Check if path is within safe directories (optional - can be configured)
        # For now, we'll allow any path but log warnings for unusual locations

        return path_obj

    def _sanitize_options(self, options: dict[str, str | int | float | bool]) -> dict[str, str | int | float | bool]:
        """Sanitize options to prevent command injection and ensure safety."""
        safe_options = {}

        # Allowed HandBrake CLI options to prevent injection
        allowed_keys = {
            "quality",
            "encoder",
            "vb",
            "audio",
            "audio-lang-list",
            "all-audio",
            "native-language",
            "native-dub",
            "ab",
            "ar",
            "acodec",
            "aname",
            "aencoder",
            "subtitle",
            "subtitle-forced",
            "subtitle-burned",
            "subtitle-default",
            "srt-file",
            "srt-codeset",
            "srt-offset",
            "srt-lang",
            "srt-default",
            "scodec",
            "sencoder",
            "width",
            "height",
            "maxWidth",
            "maxHeight",
            "crop",
            "deinterlace",
            "denoise",
            "deblock",
            "colorspace",
            "format",
            "optimize",
            "ipod-atom",
            "use-opencl",
            "use-qsv",
            "use-nvenc",
            "preset",
            "input",
            "output",
        }

        for key, value in options.items():
            # Validate key against allowed options
            safe_key = str(key).strip()
            if safe_key not in allowed_keys:
                logger.warning(f"Unknown or potentially unsafe option: {safe_key}")
                continue

            # Sanitize key by removing dangerous characters
            safe_key = "".join(c for c in safe_key if c.isalnum() or c in ["-", "_"])

            # Sanitize value based on type
            if isinstance(value, bool):
                safe_value = value
            elif isinstance(value, (int, float)):
                # Validate numeric ranges
                if isinstance(value, int) and not (-1000000 <= value <= 1000000):
                    logger.warning(f"Integer value out of safe range: {value}")
                    continue
                if isinstance(value, float) and not (-1000000.0 <= value <= 1000000.0):
                    logger.warning(f"Float value out of safe range: {value}")
                    continue
                safe_value = value
            else:
                # Sanitize string values
                safe_value = str(value).strip()
                if len(safe_value) > self._max_option_value_length:
                    logger.warning(
                        f"Option value too long: {len(safe_value)} chars (max: {self._max_option_value_length})"
                    )
                    continue
                # Remove dangerous characters that could be used for injection
                safe_value = "".join(
                    c for c in safe_value if c not in [";", "&", "|", "`", "$", "(", ")", "<", ">", '"', "'"]
                )

            safe_options[safe_key] = safe_value

        return safe_options

    async def _check_system_resources(self):
        """Check system resources before starting a new job."""
        try:
            import psutil
        except ImportError:
            # If psutil is not available, skip resource checking
            logger.warning("psutil not available - skipping resource checks")
            return

        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 90:
            raise ValueError(f"System CPU usage too high: {cpu_percent:.1f}% (threshold: 90%)")

        # Check memory usage
        memory = psutil.virtual_memory()
        if memory.percent > 85:
            raise ValueError(f"System memory usage too high: {memory.percent:.1f}% (threshold: 85%)")

        # Check disk space for output directory
        try:
            output_disk = psutil.disk_usage(str(self.handbrake_path.parent))
            if output_disk.percent > 90:
                raise ValueError(f"Disk space usage too high: {output_disk.percent:.1f}% (threshold: 90%)")
        except Exception as e:
            # If we can't check disk space, continue anyway
            logger.warning(f"Disk-space check skipped: {e}")

    @staticmethod
    def _extract_progress(transcript: str) -> float | None:
        """Last ``Progress.Working.Progress`` from a ``--json`` transcript.

        HandBrakeCLI pretty-prints ``Progress: { ... "Working": {
        "Progress": 0.42 ... } }`` blocks (the value is a 0..1 fraction);
        anything else on stdout (``Version: {...}``, scan logs) is ignored.
        Returns the value normalized to the 0..100 job scale, or None when no
        complete progress block is present yet.
        """
        best: float | None = None
        buf: list[str] = []
        for raw in transcript.splitlines():
            stripped = raw.strip()
            if not buf:
                if not stripped.startswith("Progress:"):
                    continue
                buf = [stripped[len("Progress:") :]]
            else:
                buf.append(raw)
            chunk = "".join(buf)
            if chunk.count("{") > chunk.count("}"):
                continue  # incomplete object, keep buffering
            try:
                data = json.loads(chunk)
            except ValueError:
                buf = []
                continue
            buf = []
            if not isinstance(data, dict):
                continue
            # Real CLI 1.x: `Progress: {"State": ..., "Working": {"Progress": x}}`
            # (the "Working" block sits directly under the "Progress:"-prefixed
            # object); tolerate an older wrapper shape if encountered.
            working = data.get("Working") if isinstance(data.get("Working"), dict) else None
            prog = data.get("Progress")
            if working is None and isinstance(prog, dict):
                working = prog.get("Working") if isinstance(prog.get("Working"), dict) else None
            val = working.get("Progress") if working else None
            if isinstance(val, bool):
                continue
            if isinstance(val, (int, float)):
                best = round(float(val) * 100.0, 1) if float(val) <= 1.0 else float(val)
        return best

    async def _run_transcode_job(self, job: TranscodeJob):
        """Run a transcoding job in the background."""
        try:
            job.status = "processing"

            # Prepare output directory
            job.output_path.parent.mkdir(parents=True, exist_ok=True)

            # Build HandBrakeCLI command with security measures
            cmd = [
                str(self.handbrake_path),
                "--input",
                str(job.input_path),
                "--output",
                str(job.output_path),
                "--preset-import-gui",
                "--preset",
                job.preset,
                "--json",
            ]

            # Add additional options (already sanitized)
            for key, value in job.options.items():
                if value is True:
                    cmd.append(f"--{key}")
                elif value is not False and value is not None:
                    cmd.extend([f"--{key}", str(value)])

            # Start the process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            job.process = process

            # Process output. NOTE: HandBrakeCLI --json emits *pretty-printed*
            # multi-line objects prefixed with "Progress:", not single-line
            # JSON, e.g.:  Progress: {\n  "Working": {\n ... "Progress": 0.42
            # (a 0..1 fraction). Buffer the transcript and re-extract the
            # latest value whenever a line could complete a block. (When stdout
            # is a pipe, libc block-buffering means short encodes may deliver
            # everything at exit — the completion path below still sets 100.)
            transcript_parts: list[str] = []
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                text = line.decode(errors="replace")
                transcript_parts.append(text)
                if "}" in text:
                    val = self._extract_progress("".join(transcript_parts))
                    if val is not None:
                        job.progress = val

            # Wait for process to complete
            await process.wait()

            if job.status == "cancelled":
                # cancel_job() won the race while the process was exiting.
                # Leave the terminal state alone instead of overwriting it.
                logger.info(f"Transcoding cancelled (exit raced): {job.job_id}")
                return

            if process.returncode == 0:
                job.status = "completed"
                job.progress = 100.0
                logger.info(f"Transcoding completed: {job.job_id}")
            else:
                error_output = await process.stderr.read()
                job.status = "failed"
                job.error = f"HandBrakeCLI failed with code {process.returncode}: {error_output.decode()}"
                logger.error(f"Transcoding failed: {job.job_id} - {job.error}")

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            logger.exception(f"Error in transcode job {job.job_id}")

    async def get_job_status(self, job_id: str) -> TranscodeJob | None:
        """Get the status of a transcoding job."""
        return self.jobs.get(job_id)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running transcoding job."""
        job = self.jobs.get(job_id)
        if not job or not job.process:
            return False

        try:
            job.process.terminate()
            await asyncio.wait_for(job.process.wait(), timeout=5.0)
        except (TimeoutError, ProcessLookupError):
            job.process.kill()
            await job.process.wait()

        job.status = "cancelled"
        return True

    async def _run_handbrake(self, args: list[str]) -> str:
        """Run HandBrakeCLI with the given arguments.

        HandBrakeCLI writes informational output (including ``--preset-list``)
        to *stderr*, so when stdout is empty on success the stderr text is
        returned instead. Callers that parse structured stdout (JSON progress)
        never use this helper — only one-shot queries do.
        """
        cmd = [str(self.handbrake_path), *args]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode().strip() or "Unknown error"
            raise HandBrakeError(f"HandBrakeCLI failed: {error_msg}")

        text = stdout.decode().strip()
        if not text:
            text = stderr.decode().strip()
        return text


# Global instance - lazy initialization
handbrake_service = None


def get_handbrake_service():
    """Get the HandBrake service instance, initializing it if necessary."""
    global handbrake_service
    if handbrake_service is None:
        handbrake_service = HandBrakeService()
    return handbrake_service
