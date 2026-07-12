import sys

from doctoskill.cli import main


def run() -> int:
    try:
        return main()
    except KeyboardInterrupt:
        print("\n[mentor] Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(run())
