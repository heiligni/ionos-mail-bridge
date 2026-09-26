"""Start the repository's MCP server through uv without emitting to stdout."""

import os
import shutil
import sys
from pathlib import Path


def main() -> None:
    project = Path(__file__).resolve().parents[3]
    uv = shutil.which("uv")
    if uv:
        os.environ.setdefault("UV_CACHE_DIR", str(project / ".uv-cache"))
        os.execv(uv, [uv, "run", "--project", str(project), "--extra", "mcp", "ionos-mail-mcp"])
    executable = shutil.which("ionos-mail-mcp")
    if executable:
        os.execv(executable, [executable])
    print("Install uv or put an installed ionos-mail-mcp on PATH", file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
