"""Transcription support (stcc speech-to-captions).

The stcc package is bundled and installed via ``filesqueeze setup-deps``
(see :mod:`filesqueeze.deps_setup`), but the processing pipeline does not
generate captions yet. This module currently only reports the package's
presence at startup so installations are visible in the log; caption
generation will build on it in a future release.
"""

import logging
from pathlib import Path


def get_stcc_path(config) -> str:
    """Return the configured stcc.py path ('' when not configured)."""
    return str(config.get("transcription.stcc_path", "") or "")


def log_stcc_status(config, logger: logging.Logger) -> None:
    """Log whether the optional stcc captions package is present.

    Called once at service startup. The pipeline does not use stcc yet —
    this is purely an installation-visibility check.
    """
    path = get_stcc_path(config)
    if not path:
        logger.info("stcc captions package: not configured (optional — install via 'filesqueeze setup-deps')")
    elif Path(path).exists():
        logger.info("stcc captions package available (not yet used): %s", path)
    else:
        logger.warning("stcc captions package configured but missing: %s", path)
