"""Transcription support (stcc speech-to-captions).

The stcc package is bundled and installed via ``filesqueeze setup-deps``
(see :mod:`filesqueeze.deps_setup`). This module reports the package's
presence at service startup; caption generation itself lives in
:mod:`filesqueeze.ops.transcription` and runs post-compress when
``[transcription] enabled`` is true.
"""

import logging
from pathlib import Path


def get_stcc_path(config) -> str:
    """Return the configured stcc.py path ('' when not configured)."""
    return str(config.get("transcription.stcc_path", "") or "")


def log_stcc_status(config, logger: logging.Logger) -> None:
    """Log whether the optional stcc captions package is present.

    Called once at service startup so installations are visible in the log.
    """
    path = get_stcc_path(config)
    if not path:
        logger.info("stcc captions package: not configured (optional — install via 'filesqueeze setup-deps')")
    elif Path(path).exists():
        logger.info("stcc captions package available: %s", path)
    else:
        logger.warning("stcc captions package configured but missing: %s", path)
