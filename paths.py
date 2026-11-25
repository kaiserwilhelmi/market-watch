"""Where the data lives. The scheduled collector keeps it on a separate `data` branch,
checked out beside the code and named in MW_DATA_DIR; without that it is ./data."""
import os
from pathlib import Path

HERE = Path(__file__).parent
DATA = Path(os.environ.get("MW_DATA_DIR") or HERE / "data")
