"""Fail-closed Kilo availability check; no CLI process is started.

Kilo's free primary model does not prove background usage is free. Kilo's
configuration and account permissions cannot be independently verified here.
Do not enable unattended execution until the effective provider, primary and
small model, account spending, tool permissions, workspace isolation and
request limits are verified for the actual session.

References: https://kilo.ai/docs/getting-started/using-kilo-for-free and
https://kilo.ai/docs/code-with-ai/platforms/cli
"""
from dataclasses import dataclass
import shutil


@dataclass(frozen=True)
class KiloStatus:
    installed: bool
    available: bool
    reason: str


def assess_kilo() -> KiloStatus:
    """Check PATH only; does not inspect credentials or claim authentication."""
    if shutil.which('kilo') is None:
        return KiloStatus(False, False, 'Kilo CLI is not installed on PATH')
    return KiloStatus(True, False,
                      'Kilo is not enabled: account billing and background model are unverified; '
                      'workspace isolation and quota integration are required')


def prepare_kilo_run(task: str):
    """Fail closed until the execution and verification mechanisms exist."""
    raise RuntimeError('Kilo execution is not enabled: ' + assess_kilo().reason)
