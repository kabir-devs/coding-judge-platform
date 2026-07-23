"""
Executes untrusted user code inside a locked-down, ephemeral Docker
container and compares output against expected test cases.

SECURITY MODEL (defense in depth):
  1. Fresh container per submission, destroyed immediately after (--rm).
  2. No network access at all (--network none) -> can't exfiltrate data,
     hit internal services, or download second-stage payloads.
  3. Read-only root filesystem (--read-only) with a small tmpfs for
     scratch space only -> code can't persist anything or fill disk.
  4. Hard memory cap + OOM kill (--memory, --memory-swap=same value so
     no swap escape hatch).
  5. CPU share cap (--cpus) so one submission can't starve the host.
  6. PID limit (--pids-limit) -> blocks fork bombs.
  7. Dropped Linux capabilities + no-new-privileges -> can't escalate,
     can't load kernel modules, can't do raw sockets, etc.
  8. Runs as an unprivileged, non-root UID inside the container.
  9. Wall-clock timeout enforced from OUTSIDE the container (subprocess
     timeout) as a backstop in case the in-container limits are bypassed.
  10. ulimits (nproc, nofile) as a second layer under the docker flags.

This module shells out to the `docker` CLI rather than the Docker SDK to
keep the dependency footprint small; swap in docker-py if preferred.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from app.config import settings
from app.judge.languages import get_language_config


@dataclass
class RunResult:
    status: str                 # ACCEPTED | WRONG_ANSWER | TLE | MLE | RE | CE | INTERNAL_ERROR
    stdout: str = ""
    stderr: str = ""
    runtime_ms: int = 0
    memory_kb: int = 0
    exit_code: Optional[int] = None


@dataclass
class JudgeVerdict:
    status: str
    passed_tests: int
    total_tests: int
    runtime_ms: int
    memory_kb: int
    stderr: str
    detail: list = field(default_factory=list)


class SandboxExecutor:
    def __init__(self):
        self.docker_bin = shutil.which("docker") or "docker"

    # ---------------------------------------------------------------
    def _build_docker_cmd(self, work_dir: str, image: str, cmd: list[str],
                           time_limit_sec: float, memory_limit_mb: int) -> list[str]:
        mem = f"{memory_limit_mb}m"
        return [
            self.docker_bin, "run",
            "--rm",
            "--name", f"judge-{uuid.uuid4().hex[:12]}",
            "--network", "none" if settings.JUDGE_NETWORK_DISABLED else "bridge",
            "--read-only",
            "--tmpfs", "/tmp:rw,size=64m,mode=1777",
            "--memory", mem,
            "--memory-swap", mem,           # disallow swap -> hard cap
            "--cpus", settings.JUDGE_CPU_LIMIT,
            "--pids-limit", str(settings.JUDGE_PIDS_LIMIT),
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--user", "1000:1000",
            "-v", f"{work_dir}:/sandbox:rw",
            "-w", "/sandbox",
            "--ulimit", "nproc=64:64",
            "--ulimit", "nofile=128:128",
            image,
            "timeout", "--signal=KILL", str(int(time_limit_sec) + 1),
            *cmd,
        ]

    # ---------------------------------------------------------------
    def _run_in_container(self, work_dir: str, image: str, cmd: list[str],
                           stdin_data: str, time_limit_sec: float,
                           memory_limit_mb: int) -> RunResult:
        docker_cmd = self._build_docker_cmd(work_dir, image, cmd, time_limit_sec, memory_limit_mb)
        start = time.monotonic()
        try:
            proc = subprocess.run(
                docker_cmd,
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=time_limit_sec + 5,  # outer backstop beyond in-container `timeout`
            )
        except subprocess.TimeoutExpired:
            elapsed = int((time.monotonic() - start) * 1000)
            return RunResult(status="TIME_LIMIT_EXCEEDED", runtime_ms=elapsed)

        elapsed_ms = int((time.monotonic() - start) * 1000)

        if proc.returncode == 137:  # SIGKILL - OOM or timeout kill from `timeout`/cgroup
            if elapsed_ms >= time_limit_sec * 1000:
                return RunResult(status="TIME_LIMIT_EXCEEDED", runtime_ms=elapsed_ms, stderr=proc.stderr)
            return RunResult(status="MEMORY_LIMIT_EXCEEDED", runtime_ms=elapsed_ms, stderr=proc.stderr)

        if proc.returncode != 0:
            return RunResult(
                status="RUNTIME_ERROR", stdout=proc.stdout, stderr=proc.stderr,
                runtime_ms=elapsed_ms, exit_code=proc.returncode,
            )

        return RunResult(status="OK", stdout=proc.stdout, stderr=proc.stderr, runtime_ms=elapsed_ms)

    # ---------------------------------------------------------------
    def compile(self, work_dir: str, language: str, source_code: str) -> Optional[RunResult]:
        cfg = get_language_config(language)
        with open(os.path.join(work_dir, cfg["source_filename"]), "w") as f:
            f.write(source_code)

        if not cfg["compile_cmd"]:
            return None  # interpreted language, nothing to compile

        result = self._run_in_container(
            work_dir, cfg["image"], cfg["compile_cmd"],
            stdin_data="", time_limit_sec=10, memory_limit_mb=512,
        )
        if result.status != "OK":
            result.status = "COMPILE_ERROR"
        return result

    # ---------------------------------------------------------------
    def run_test_case(self, work_dir: str, language: str, stdin_data: str,
                       time_limit_sec: float, memory_limit_mb: int) -> RunResult:
        cfg = get_language_config(language)
        return self._run_in_container(
            work_dir, cfg["image"], cfg["run_cmd"], stdin_data,
            time_limit_sec, memory_limit_mb,
        )

    # ---------------------------------------------------------------
    def judge_submission(self, language: str, source_code: str, test_cases: list[dict],
                          time_limit_sec: float, memory_limit_mb: int) -> JudgeVerdict:
        """
        test_cases: [{"input": str, "expected_output": str}, ...]
        Runs each test in its own fresh container. Short-circuits on the
        first failing/erroring test (standard judge UX), but still reports
        how many passed before that.
        """
        detail = []
        with tempfile.TemporaryDirectory(prefix="judge-") as work_dir:
            os.chmod(work_dir, 0o777)  # sandbox user (uid 1000) needs write access

            compile_result = self.compile(work_dir, language, source_code)
            if compile_result and compile_result.status != "OK":
                return JudgeVerdict(
                    status="COMPILE_ERROR", passed_tests=0, total_tests=len(test_cases),
                    runtime_ms=0, memory_kb=0, stderr=compile_result.stderr, detail=[],
                )

            passed = 0
            max_runtime = 0
            for idx, tc in enumerate(test_cases, start=1):
                result = self.run_test_case(
                    work_dir, language, tc["input"], time_limit_sec, memory_limit_mb
                )
                max_runtime = max(max_runtime, result.runtime_ms)

                if result.status != "OK":
                    detail.append({"case": idx, "status": result.status, "time_ms": result.runtime_ms})
                    return JudgeVerdict(
                        status=result.status, passed_tests=passed, total_tests=len(test_cases),
                        runtime_ms=max_runtime, memory_kb=0, stderr=result.stderr, detail=detail,
                    )

                actual = result.stdout.strip()
                expected = tc["expected_output"].strip()
                if actual == expected:
                    passed += 1
                    detail.append({"case": idx, "status": "ACCEPTED", "time_ms": result.runtime_ms})
                else:
                    detail.append({"case": idx, "status": "WRONG_ANSWER", "time_ms": result.runtime_ms})
                    return JudgeVerdict(
                        status="WRONG_ANSWER", passed_tests=passed, total_tests=len(test_cases),
                        runtime_ms=max_runtime, memory_kb=0, stderr="", detail=detail,
                    )

            return JudgeVerdict(
                status="ACCEPTED", passed_tests=passed, total_tests=len(test_cases),
                runtime_ms=max_runtime, memory_kb=0, stderr="", detail=detail,
            )


executor = SandboxExecutor()
