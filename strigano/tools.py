"""Safe external-tool execution with graceful handling of missing tools.

Every call to an external binary (exiftool, binwalk, steghide, ...) goes
through :func:`run_tool`. If the binary is not installed, the result simply
reports ``available=False`` and the caller renders a "not installed" notice
instead of the whole analysis crashing. This is what lets the same codebase
run fully on a Kali VM and in a reduced mode on a bare Windows box.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field

from . import config


@dataclass
class ToolResult:
    """Outcome of one external-tool invocation."""

    tool: str
    available: bool = True
    ok: bool = False
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    error: str = ""

    @property
    def summary(self) -> str:
        """A short human line describing what happened, for CLI and templates."""
        if not self.available:
            return f"{self.tool} is not installed (skipped)."
        if self.error:
            return f"{self.tool} failed: {self.error}"
        if self.ok:
            return f"{self.tool} ran successfully."
        return f"{self.tool} exited with code {self.returncode}."


def resolve(tool: str) -> str | None:
    """Return the runnable path for a configured tool, or None if absent.

    Honours an absolute path set via config/env, otherwise searches PATH.
    """
    command = config.TOOLS.get(tool, tool)
    # An explicit path that exists wins outright.
    direct = shutil.which(command)
    if direct:
        return direct
    return None


def is_available(tool: str) -> bool:
    return resolve(tool) is not None


def tool_status() -> dict[str, bool]:
    """Availability map for every configured tool, for `strigano check`/`/tools`."""
    return {name: is_available(name) for name in config.TOOLS}


def run_tool(
    tool: str,
    args: list[str],
    *,
    timeout: int | None = None,
    cwd: str | None = None,
    success_returncodes: tuple[int, ...] = (0,),
) -> ToolResult:
    """Run ``<tool> <args...>`` and never raise for an absent or failing tool.

    Parameters
    ----------
    tool:
        Logical name, looked up in :data:`config.TOOLS`.
    args:
        Arguments after the executable.
    success_returncodes:
        Return codes treated as success (some tools use non-zero for "found
        nothing" rather than error).
    """
    path = resolve(tool)
    if path is None:
        return ToolResult(tool=tool, available=False)

    timeout = timeout if timeout is not None else config.TOOL_TIMEOUT
    try:
        proc = subprocess.run(
            [path, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(tool=tool, error=f"timed out after {timeout}s")
    except OSError as exc:  # permission, exec format, etc.
        return ToolResult(tool=tool, error=str(exc))

    return ToolResult(
        tool=tool,
        ok=proc.returncode in success_returncodes,
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )
