from __future__ import annotations

# Backward-compatible shim: existing launchers import/use this module.
from apps.api.server import *  # noqa: F401,F403
from apps.api.server import main


if __name__ == "__main__":
    main()
