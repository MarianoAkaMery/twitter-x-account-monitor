import json

from .config import load_config
from .logging_setup import setup_logging
from .x_client import XClient


def main() -> None:
    config = load_config()
    setup_logging(config.log_level, config.log_file)
    usage = XClient(config).get_usage()
    print(json.dumps(usage, indent=2, sort_keys=True))
