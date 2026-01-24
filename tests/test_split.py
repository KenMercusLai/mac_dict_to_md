"""Tests for mac_dict_to_md.split module."""

from pathlib import Path

import pytest

from mac_dict_to_md import split
from mac_dict_to_md.split import Entry


# ============================================================================
# Filename Generation Tests
# ============================================================================


class TestMakeFilename:
    """Tests for make_filename function."""

    def test_simple_word(self):
        entry = Entry(title="hello", homograph=None, content="")
        assert split.make_filename(entry) == "hello.xml"

    def test_with_homograph(self):
        entry = Entry(title="bow", homograph="1", content="")
        assert split.make_filename(entry) == "bow_1.xml"

    def test_sanitizes_slash(self):
        entry = Entry(title="either/or", homograph=None, content="")
        assert split.make_filename(entry) == "either_or.xml"

    def test_sanitizes_backslash(self):
        entry = Entry(title="foo\\bar", homograph=None, content="")
        assert split.make_filename(entry) == "foo_bar.xml"

    def test_sanitizes_colon(self):
        entry = Entry(title="foo:bar", homograph=None, content="")
        assert split.make_filename(entry) == "foo_bar.xml"

    def test_sanitizes_asterisk(self):
        entry = Entry(title="foo*bar", homograph=None, content="")
        assert split.make_filename(entry) == "foo_bar.xml"

    def test_sanitizes_question_mark(self):
        entry = Entry(title="what?", homograph=None, content="")
        assert split.make_filename(entry) == "what_.xml"

    def test_sanitizes_quotes(self):
        entry = Entry(title='say "hello"', homograph=None, content="")
        assert split.make_filename(entry) == "say _hello_.xml"

    def test_sanitizes_angle_brackets(self):
        entry = Entry(title="<tag>", homograph=None, content="")
        assert split.make_filename(entry) == "_tag_.xml"

    def test_sanitizes_pipe(self):
        entry = Entry(title="a|b", homograph=None, content="")
        assert split.make_filename(entry) == "a_b.xml"

    def test_strips_whitespace(self):
        entry = Entry(title="  word  ", homograph=None, content="")
        assert split.make_filename(entry) == "word.xml"

    def test_homograph_with_special_chars(self):
        entry = Entry(title="either/or", homograph="2", content="")
        assert split.make_filename(entry) == "either_or_2.xml"


# ============================================================================
# Extraction Function Tests
# ============================================================================


class TestExtractTitle:
    """Tests for extract_title function."""

    def test_finds_d_title(self):
        content = '<d:entry class="entry" d:title="hello">content</d:entry>'
        assert split.extract_title(content) == "hello"

    def test_returns_empty_when_missing(self):
        content = '<d:entry class="entry">content</d:entry>'
        assert split.extract_title(content) == ""

    def test_handles_special_chars_in_title(self):
        content = '<d:entry d:title="either/or">content</d:entry>'
        assert split.extract_title(content) == "either/or"

    def test_handles_title_with_quotes(self):
        content = '<d:entry d:title="it&apos;s">content</d:entry>'
        # Note: this extracts the raw attribute value
        assert "it" in split.extract_title(content)


class TestExtractHomograph:
    """Tests for extract_homograph function."""

    def test_finds_homograph_number(self):
        content = '<d:entry><span class="hw" homograph="1">word</span></d:entry>'
        assert split.extract_homograph(content) == "1"

    def test_returns_none_when_missing(self):
        content = '<d:entry><span class="hw">word</span></d:entry>'
        assert split.extract_homograph(content) is None

    def test_handles_attribute_order_class_first(self):
        content = '<d:entry><span class="hw" homograph="2">word</span></d:entry>'
        assert split.extract_homograph(content) == "2"

    def test_handles_attribute_order_homograph_first(self):
        content = '<d:entry><span homograph="3" class="hw">word</span></d:entry>'
        assert split.extract_homograph(content) == "3"

    def test_multi_digit_homograph(self):
        content = '<d:entry><span class="hw" homograph="12">word</span></d:entry>'
        assert split.extract_homograph(content) == "12"


# ============================================================================
# Entry Processing Tests
# ============================================================================


class TestFindEntries:
    """Tests for find_entries function."""

    def test_yields_all_entries(self):
        content = """
        <dictionary>
            <d:entry d:title="alpha">first</d:entry>
            <d:entry d:title="beta">second</d:entry>
            <d:entry d:title="gamma">third</d:entry>
        </dictionary>
        """
        entries = list(split.find_entries(content))
        assert len(entries) == 3
        assert entries[0].title == "alpha"
        assert entries[1].title == "beta"
        assert entries[2].title == "gamma"

    def test_skips_entries_without_title(self):
        content = """
        <dictionary>
            <d:entry d:title="valid">content</d:entry>
            <d:entry>no title</d:entry>
            <d:entry d:title="">empty title</d:entry>
            <d:entry d:title="   ">whitespace title</d:entry>
        </dictionary>
        """
        entries = list(split.find_entries(content))
        assert len(entries) == 1
        assert entries[0].title == "valid"

    def test_extracts_homograph(self):
        content = '<d:entry d:title="bow"><span class="hw" homograph="1">bow</span></d:entry>'
        entries = list(split.find_entries(content))
        assert len(entries) == 1
        assert entries[0].homograph == "1"

    def test_handles_multiline_entries(self):
        content = """
        <d:entry d:title="multiline">
            <span class="content">
                multiple
                lines
            </span>
        </d:entry>
        """
        entries = list(split.find_entries(content))
        assert len(entries) == 1
        assert "multiple" in entries[0].content

    def test_handles_empty_content(self):
        content = ""
        entries = list(split.find_entries(content))
        assert len(entries) == 0


class TestSaveEntry:
    """Tests for save_entry function."""

    def test_creates_file(self, temp_output_dir: Path):
        entry = Entry(title="test", homograph=None, content="<d:entry>content</d:entry>")
        filepath = split.save_entry(entry, temp_output_dir)
        assert filepath.exists()
        assert filepath.read_text() == "<d:entry>content</d:entry>"

    def test_uses_correct_filename(self, temp_output_dir: Path):
        entry = Entry(title="myword", homograph=None, content="content")
        filepath = split.save_entry(entry, temp_output_dir)
        assert filepath.name == "myword.xml"

    def test_uses_homograph_in_filename(self, temp_output_dir: Path):
        entry = Entry(title="bow", homograph="2", content="content")
        filepath = split.save_entry(entry, temp_output_dir)
        assert filepath.name == "bow_2.xml"


class TestProcessEntries:
    """Tests for process_entries function."""

    def test_yields_paths(self, temp_output_dir: Path):
        entries = [
            Entry(title="one", homograph=None, content="<entry>1</entry>"),
            Entry(title="two", homograph=None, content="<entry>2</entry>"),
        ]
        paths = list(split.process_entries(iter(entries), temp_output_dir))
        assert len(paths) == 2
        assert all(p.exists() for p in paths)


class TestSplitDictionary:
    """Tests for split_dictionary function."""

    def test_processes_all_entries(self, temp_output_dir: Path):
        # Create a test dictionary file
        dict_content = """
        <dictionary>
            <d:entry d:title="alpha">first</d:entry>
            <d:entry d:title="beta">second</d:entry>
        </dictionary>
        """
        input_file = temp_output_dir / "test_dict.xml"
        input_file.write_text(dict_content)

        output_subdir = temp_output_dir / "output"
        count = split.split_dictionary(input_file, output_subdir)

        assert count == 2
        assert (output_subdir / "alpha.xml").exists()
        assert (output_subdir / "beta.xml").exists()

    def test_creates_output_directory(self, temp_output_dir: Path):
        dict_content = '<d:entry d:title="word">content</d:entry>'
        input_file = temp_output_dir / "dict.xml"
        input_file.write_text(dict_content)

        output_subdir = temp_output_dir / "new_dir" / "nested"
        count = split.split_dictionary(input_file, output_subdir)

        assert output_subdir.exists()
        assert count == 1


class TestEntry:
    """Tests for Entry NamedTuple."""

    def test_fields(self):
        entry = Entry(title="word", homograph="1", content="<entry/>")
        assert entry.title == "word"
        assert entry.homograph == "1"
        assert entry.content == "<entry/>"

    def test_none_homograph(self):
        entry = Entry(title="word", homograph=None, content="<entry/>")
        assert entry.homograph is None
