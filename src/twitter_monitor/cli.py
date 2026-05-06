from .config import load_config
from .monitor import Monitor


def main() -> None:
    Monitor(load_config()).run()
