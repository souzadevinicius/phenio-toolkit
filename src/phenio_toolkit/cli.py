"""Command line interface for phenio_toolkit."""
import logging

import click

from phenio_toolkit import __version__
from phenio_toolkit.phenio_cli import lexical_mapping_command

__all__ = [
    "main",
]

logger = logging.getLogger(__name__)


@click.group()
@click.option("-v", "--verbose", count=True)
@click.option("-q", "--quiet")
@click.version_option(__version__)
def main(verbose: int, quiet: bool):
    """CLI for phenio_toolkit.

    :param verbose: Verbosity while running.
    :param quiet: Boolean to be quiet or verbose.
    """
    if verbose >= 2:
        logger.setLevel(level=logging.DEBUG)
    elif verbose == 1:
        logger.setLevel(level=logging.INFO)
    else:
        logger.setLevel(level=logging.WARNING)
    if quiet:
        logger.setLevel(level=logging.ERROR)


@click.group()
def phenio():
    """Phenio."""


phenio.add_command(lexical_mapping_command)


if __name__ == "__main__":
    main()
