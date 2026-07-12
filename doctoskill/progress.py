import sys


class ProgressReporter:
    """Small stderr progress reporter suitable for terminals and CI logs."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def log(self, message: str) -> None:
        if self.enabled:
            print(f"[mentor] {message}", file=sys.stderr, flush=True)
