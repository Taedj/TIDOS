"""Entry point usable both as `python -m tidos_scout` and `python path/to/tidos_scout/__main__.py`."""
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tidos_scout.cli import main  # noqa: E402

sys.exit(main())
