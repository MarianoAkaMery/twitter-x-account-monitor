import json

from .config import load_config
from .x_client import XClient


def main() -> None:
    usage = XClient(load_config()).get_usage()
    print(json.dumps(usage, indent=2, sort_keys=True))
