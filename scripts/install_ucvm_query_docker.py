#!/usr/bin/env python3
"""Install a lightweight ``ucvm_query`` wrapper backed by a SCEC Docker image.

This does not vendor or redistribute UCVM model data. It writes a small shell
script that calls Docker; the SCEC image is pulled by Docker on first use, or
immediately when ``--pull`` is supplied.
"""
from __future__ import annotations

import argparse
import shutil
import stat
import subprocess
from pathlib import Path

DEFAULT_IMAGE = "sceccode/ucvm_257_cvmsi:0801"
DEFAULT_TARGET = Path(".codameter/bin/ucvm_query")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a local ucvm_query command that runs SCEC UCVM via Docker."
    )
    parser.add_argument(
        "--image",
        default=DEFAULT_IMAGE,
        help=f"Docker image to use (default: {DEFAULT_IMAGE})",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TARGET,
        help=f"Wrapper path to create (default: {DEFAULT_TARGET})",
    )
    parser.add_argument(
        "--pull",
        action="store_true",
        help="Pull the Docker image now instead of waiting for first query.",
    )
    args = parser.parse_args()

    docker = shutil.which("docker")
    if docker is None:
        raise SystemExit(
            "Docker was not found on PATH. Install Docker Desktop or a compatible "
            "Docker client before using the UCVM Docker option."
        )

    if args.pull:
        subprocess.run([docker, "pull", args.image], check=True)

    target = args.target.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "#!/usr/bin/env sh\n"
        "set -eu\n"
        f"exec {docker!s} run --rm -i {args.image!s} ucvm_query \"$@\"\n"
    )
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"Installed UCVM Docker wrapper: {target}")
    print("Use it in codameter configs with:")
    print("  property_sources:")
    print("    ucvm:")
    print(f"      executable: {target}")
    print("or add this directory to PATH:")
    print(f"  export PATH=\"{target.parent}:$PATH\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
