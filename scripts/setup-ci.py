#!/usr/bin/env python3
"""
CI/CD Setup Script for HandBrake MCP Server.

This script helps set up the CI/CD pipeline and validates the configuration.
"""

import sys
from pathlib import Path


def emit(message: str = "") -> None:
    """Write one console line. (Ruff T201: `print` is banned repo-wide.)"""
    sys.stdout.write(message + "\n")


def check_github_actions():
    """Check GitHub Actions setup."""
    emit("Checking GitHub Actions...")

    workflows_dir = Path(".github/workflows")
    if not workflows_dir.exists():
        emit("ERROR: .github/workflows directory not found")
        return False

    required_files = ["ci.yml", "version-management.yml", "dependency-updates.yml", "docker.yml"]

    missing_files = []
    for name in required_files:
        if not (workflows_dir / name).exists():
            missing_files.append(name)

    if missing_files:
        emit(f"ERROR: Missing workflow files: {', '.join(missing_files)}")
        return False

    emit("OK: GitHub Actions workflows found")
    return True


def check_docker_setup():
    """Check Docker setup."""
    emit("Checking Docker setup...")

    dockerfile = Path("Dockerfile")
    if not dockerfile.exists():
        emit("ERROR: Dockerfile not found")
        return False

    if not Path("docker-compose.yml").exists():
        emit("NOTE: docker-compose.yml not found (optional)")

    emit("OK: Docker setup found")
    return True


def check_kubernetes_setup():
    """Check Kubernetes setup."""
    emit("Checking Kubernetes setup...")

    k8s_dir = Path("k8s")
    if not k8s_dir.exists():
        emit("NOTE: k8s directory not found (optional)")
        return True

    required_k8s_files = ["deployment.yml", "service.yml", "ingress.yml", "pvc.yml", "configmap.yml"]

    missing_files = []
    for name in required_k8s_files:
        if not (k8s_dir / name).exists():
            missing_files.append(name)

    if missing_files:
        emit(f"NOTE: Missing Kubernetes files: {', '.join(missing_files)}")
    else:
        emit("OK: Kubernetes setup found")

    return True


def check_monitoring_setup():
    """Check monitoring setup."""
    emit("Checking monitoring setup...")

    monitoring_dir = Path("monitoring")
    if not monitoring_dir.exists():
        emit("NOTE: monitoring directory not found (optional)")
        return True

    if (monitoring_dir / "prometheus.yml").exists():
        emit("OK: Prometheus configuration found")

    if (monitoring_dir / "grafana" / "provisioning").exists():
        emit("OK: Grafana provisioning found")

    return True


def validate_ci_cd_setup():
    """Validate the complete CI/CD setup."""
    emit("Validating CI/CD Setup")
    emit("=" * 50)

    checks = [check_github_actions, check_docker_setup, check_kubernetes_setup, check_monitoring_setup]

    all_passed = True
    for check in checks:
        try:
            if not check():
                all_passed = False
        except Exception as exc:
            emit(f"ERROR: failed during {check.__name__}: {exc}")
            all_passed = False

    emit("=" * 50)
    if not all_passed:
        emit("ERROR: Some checks failed. Review the output above.")
        return False

    emit("OK: CI/CD setup validation passed")
    emit("")
    emit("Next steps:")
    emit("1. Enable GitHub Actions in repository settings")
    emit("2. Configure repository secrets (optional)")
    emit("3. Push to main branch to trigger CI/CD")
    emit("4. Check .github/workflows/ for workflow files")
    emit("5. See docs/CI-CD-README.md for detailed documentation")
    return True


def main():
    """Main setup function."""
    emit("HandBrake MCP Server - CI/CD Setup Validation")
    emit("=" * 50)

    try:
        return 0 if validate_ci_cd_setup() else 1
    except KeyboardInterrupt:
        emit("")
        emit("NOTE: Setup interrupted by user")
        return 1
    except Exception as exc:
        emit("")
        emit(f"ERROR: Setup failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
