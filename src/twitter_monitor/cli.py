from .config import load_config
from .logging_setup import setup_logging
from .monitor import Monitor


def main() -> None:
    config = load_config()
    setup_logging(config.log_level, config.log_file)
    Monitor(config).run()
