"""Shared pytest fixtures for mac_dict_to_md tests."""

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def simple_entry_xml(fixtures_dir: Path) -> str:
    """Load simple_entry.xml fixture."""
    return (fixtures_dir / "simple_entry.xml").read_text(encoding="utf-8")


@pytest.fixture
def complex_entry_xml(fixtures_dir: Path) -> str:
    """Load complex_entry.xml fixture."""
    return (fixtures_dir / "complex_entry.xml").read_text(encoding="utf-8")


@pytest.fixture
def homograph_entry_xml(fixtures_dir: Path) -> str:
    """Load homograph_entry.xml fixture."""
    return (fixtures_dir / "homograph_entry.xml").read_text(encoding="utf-8")


@pytest.fixture
def fraction_entry_xml(fixtures_dir: Path) -> str:
    """Load fraction_entry.xml fixture."""
    return (fixtures_dir / "fraction_entry.xml").read_text(encoding="utf-8")


@pytest.fixture
def special_chars_entry_xml(fixtures_dir: Path) -> str:
    """Load special_chars_entry.xml fixture."""
    return (fixtures_dir / "special_chars_entry.xml").read_text(encoding="utf-8")


@pytest.fixture
def simple_entry_element(simple_entry_xml: str) -> ET.Element:
    """Parse simple_entry.xml into an Element."""
    return ET.fromstring(simple_entry_xml)


@pytest.fixture
def complex_entry_element(complex_entry_xml: str) -> ET.Element:
    """Parse complex_entry.xml into an Element."""
    return ET.fromstring(complex_entry_xml)


@pytest.fixture
def homograph_entry_element(homograph_entry_xml: str) -> ET.Element:
    """Parse homograph_entry.xml into an Element."""
    return ET.fromstring(homograph_entry_xml)


@pytest.fixture
def fraction_entry_element(fraction_entry_xml: str) -> ET.Element:
    """Parse fraction_entry.xml into an Element."""
    return ET.fromstring(fraction_entry_xml)


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for file output tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_xml_file(temp_output_dir: Path, simple_entry_xml: str) -> Path:
    """Create a temporary XML file with simple entry content."""
    xml_path = temp_output_dir / "test_entry.xml"
    xml_path.write_text(simple_entry_xml, encoding="utf-8")
    return xml_path
