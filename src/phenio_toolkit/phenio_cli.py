"""Monarch Initiative."""
from pathlib import Path
from typing import List

import click

from phenio_toolkit.mapping.lexical_mapping import LexicalMapping


@click.command("lexical-mapping")
@click.option(
    "--species-lexical",
    "-s",
    metavar="FILE",
    required=True,
    help="Species lexical file",
    type=Path,
)
@click.option(
    "--mapping-logical",
    "-m",
    metavar="FILE",
    required=True,
    help="Mapping logical file",
    type=Path,
)
@click.option(
    "--phenotypic-effect-terms",
    "-p",
    default=["abnormally", "abnormal", "aberrant", "variant"],
    show_default=True,
    multiple=True,
    type=click.Choice(["abnormally", "abnormal", "aberrant", "variant"], case_sensitive=False),
    help="Stop Word",
)
@click.option(
    "--output",
    "-o",
    metavar="FILE",
    required=True,
    help="Output Folder",
    type=Path,
)
def lexical_mapping_command(
    species_lexical: Path, mapping_logical: Path, phenotypic_effect_terms: List[str], output: Path
) -> None:
    """lexical_mapping_command"""
    lm = LexicalMapping(species_lexical, mapping_logical, stopwords=phenotypic_effect_terms)
    lm.generate_mapping_files(output)
