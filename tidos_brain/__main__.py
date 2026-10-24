"""Entry point usable both as `python -m tidos_brain` and `python path/to/tidos_brain/__main__.py`."""
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tidos_brain.cli import main  # noqa: E402

sys.exit(main())
