"""Tests for mac_dict_to_md.convert module."""

import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import pytest

from mac_dict_to_md import convert


# ============================================================================
# XML Loading Tests
# ============================================================================


class TestLoadAndProcessXml:
    """Tests for load_and_process_xml function."""

    def test_extracts_entries(self, temp_output_dir: Path):
        xml_content = """<?xml version="1.0"?>
        <d:dictionary xmlns:d="http://www.apple.com/DTDs/DictionaryService-1.0.rng">
            <d:entry d:title="alpha">first entry</d:entry>
            <d:entry d:title="beta">second entry</d:entry>
        </d:dictionary>
        """
        xml_file = temp_output_dir / "test.xml"
        xml_file.write_text(xml_content)

        result = convert.load_and_process_xml(str(xml_file))
        assert len(result) == 2

    def test_skips_entries_without_title(self, temp_output_dir: Path):
        xml_content = """<?xml version="1.0"?>
        <d:dictionary xmlns:d="http://www.apple.com/DTDs/DictionaryService-1.0.rng">
            <d:entry d:title="valid">has title</d:entry>
            <d:entry>no title</d:entry>
        </d:dictionary>
        """
        xml_file = temp_output_dir / "test.xml"
        xml_file.write_text(xml_content)

        result = convert.load_and_process_xml(str(xml_file))
        assert len(result) == 1

    def test_skips_whitespace_only_titles(self, temp_output_dir: Path):
        xml_content = """<?xml version="1.0"?>
        <d:dictionary xmlns:d="http://www.apple.com/DTDs/DictionaryService-1.0.rng">
            <d:entry d:title="valid">has title</d:entry>
            <d:entry d:title="   ">whitespace only</d:entry>
        </d:dictionary>
        """
        xml_file = temp_output_dir / "test.xml"
        xml_file.write_text(xml_content)

        result = convert.load_and_process_xml(str(xml_file))
        assert len(result) == 1

    def test_returns_empty_on_missing_file(self, capsys):
        result = convert.load_and_process_xml("/nonexistent/path.xml")
        assert result == []

    def test_returns_empty_on_invalid_xml(self, temp_output_dir: Path, capsys):
        bad_xml = temp_output_dir / "bad.xml"
        bad_xml.write_text("not valid xml <<<<")

        result = convert.load_and_process_xml(str(bad_xml))
        assert result == []


# ============================================================================
# Find Matching Item Tests
# ============================================================================


class TestFindMatchingItem:
    """Tests for find_matching_item function."""

    def test_finds_match(self):
        items = ["apple", "banana", "cherry"]
        item, match = convert.find_matching_item(items, r"ban.*")
        assert item == "banana"
        assert match is not None

    def test_returns_none_when_not_found(self):
        items = ["apple", "banana", "cherry"]
        item, match = convert.find_matching_item(items, r"grape")
        assert item is None
        assert match is None

    def test_with_capture_groups(self):
        items = ["x_xa1", "x_xb2", "x_xc3"]
        item, match = convert.find_matching_item(items, r"x_x([a-z])(\d)")
        assert match is not None
        assert match.group(1) == "a"
        assert match.group(2) == "1"

    def test_empty_list(self):
        item, match = convert.find_matching_item([], r".*")
        assert item is None
        assert match is None


# ============================================================================
# Convert to Markdown Tests
# ============================================================================


class TestConvertToMarkdown:
    """Tests for convert_to_markdown function."""

    def test_basic_text(self):
        xml = "<span>simple text</span>"
        elem = ET.fromstring(xml)
        result = convert.convert_to_markdown(elem)
        assert "simple text" in result

    def test_italic_ex_class(self):
        xml = '<span class="ex">example text</span>'
        elem = ET.fromstring(xml)
        result = convert.convert_to_markdown(elem)
        assert "*example text*" in result

    def test_italic_ge_class(self):
        xml = '<span class="ge">glossary entry</span>'
        elem = ET.fromstring(xml)
        result = convert.convert_to_markdown(elem)
        assert "*glossary entry*" in result

    def test_italic_reg_class(self):
        xml = '<span class="reg">historical</span>'
        elem = ET.fromstring(xml)
        result = convert.convert_to_markdown(elem)
        assert "*historical*" in result

    def test_bold_l_class(self):
        xml = '<span class="l">bold word</span>'
        elem = ET.fromstring(xml)
        result = convert.convert_to_markdown(elem)
        assert "**bold word**" in result

    def test_link_conversion(self):
        xmlns = "http://www.w3.org/1999/xhtml"
        xml = f'<a xmlns="{xmlns}">linked text</a>'
        elem = ET.fromstring(xml)
        result = convert.convert_to_markdown(elem)
        assert "[[linked text]]" in result

    def test_nested_elements(self):
        # Note: convert_to_markdown processes children first, so the tail text
        # gets included inside the formatting of the child element
        xml = '<span>outer <span class="ex">inner</span> text</span>'
        elem = ET.fromstring(xml)
        result = convert.convert_to_markdown(elem)
        assert "outer" in result
        # The ex class formats its content including tail text
        assert "*inner text*" in result

    def test_nested_depth(self):
        xml = '<a><b><c>deep text</c></b></a>'
        elem = ET.fromstring(xml)
        result = convert.convert_to_markdown(elem, depth=0)
        assert "deep text" in result

    def test_section_pattern_adds_newlines(self):
        xml = '<span class="x_xd1">section content</span>'
        elem = ET.fromstring(xml)
        result = convert.convert_to_markdown(elem)
        assert "\n\n" in result

    def test_handles_tail_text(self):
        xml = '<span><span class="ex">example</span> tail text</span>'
        elem = ET.fromstring(xml)
        result = convert.convert_to_markdown(elem)
        assert "tail text" in result


# ============================================================================
# Save Entry Tests
# ============================================================================


class TestSaveEntryToMd:
    """Tests for save_entry_to_md function."""

    def test_creates_file(self, temp_output_dir: Path, monkeypatch):
        # Change to temp directory so file is created there
        monkeypatch.chdir(temp_output_dir)

        entry_xml = """
        <d:entry xmlns:d="http://www.apple.com/DTDs/DictionaryService-1.0.rng" d:title="test">
            <span>content here</span>
        </d:entry>
        """
        convert.save_entry_to_md(entry_xml)

        expected_file = temp_output_dir / "test.md"
        assert expected_file.exists()

    def test_sanitizes_filename(self, temp_output_dir: Path, monkeypatch):
        monkeypatch.chdir(temp_output_dir)

        entry_xml = """
        <d:entry xmlns:d="http://www.apple.com/DTDs/DictionaryService-1.0.rng" d:title="either/or">
            <span>content</span>
        </d:entry>
        """
        convert.save_entry_to_md(entry_xml)

        expected_file = temp_output_dir / "either_or.md"
        assert expected_file.exists()

    def test_handles_missing_title(self, capsys):
        entry_xml = '<d:entry xmlns:d="http://www.apple.com/DTDs/DictionaryService-1.0.rng"><span>no title</span></d:entry>'
        convert.save_entry_to_md(entry_xml)

        captured = capsys.readouterr()
        assert "missing" in captured.out.lower() or "Skipping" in captured.out

    def test_handles_parse_error(self, capsys):
        convert.save_entry_to_md("not valid xml <<<<")

        captured = capsys.readouterr()
        assert "parse" in captured.out.lower() or "Failed" in captured.out

    def test_handles_whitespace_title(self, capsys):
        entry_xml = '<d:entry xmlns:d="http://www.apple.com/DTDs/DictionaryService-1.0.rng" d:title="   "><span>content</span></d:entry>'
        convert.save_entry_to_md(entry_xml)

        captured = capsys.readouterr()
        assert "missing" in captured.out.lower() or "Skipping" in captured.out

    def test_file_contains_markdown(self, temp_output_dir: Path, monkeypatch):
        monkeypatch.chdir(temp_output_dir)

        entry_xml = """
        <d:entry xmlns:d="http://www.apple.com/DTDs/DictionaryService-1.0.rng" d:title="word">
            <span class="ex">example sentence</span>
        </d:entry>
        """
        convert.save_entry_to_md(entry_xml)

        content = (temp_output_dir / "word.md").read_text()
        assert "*example sentence*" in content


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_entry(self):
        xml = '<d:entry xmlns:d="http://www.apple.com/DTDs/DictionaryService-1.0.rng" d:title="empty"></d:entry>'
        elem = ET.fromstring(xml)
        result = convert.convert_to_markdown(elem)
        assert isinstance(result, str)

    def test_deeply_nested_structure(self):
        xml = "<a><b><c><d><e>deep</e></d></c></b></a>"
        elem = ET.fromstring(xml)
        result = convert.convert_to_markdown(elem)
        assert "deep" in result

    def test_multiple_classes(self):
        xml = '<span class="ex ge reg">multi class</span>'
        elem = ET.fromstring(xml)
        # First matching class wins (ex)
        result = convert.convert_to_markdown(elem)
        assert "*multi class*" in result

    def test_no_class_attribute(self):
        xml = "<span>plain</span>"
        elem = ET.fromstring(xml)
        result = convert.convert_to_markdown(elem)
        assert "plain" in result
