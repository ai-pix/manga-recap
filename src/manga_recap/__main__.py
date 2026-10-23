"""Allow `python -m manga_recap` as an entry point alongside the console script."""

from .cli import main

raise SystemExit(main())
