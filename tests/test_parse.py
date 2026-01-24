"""Tests for mac_dict_to_md.parse module."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from mac_dict_to_md import parse


# ============================================================================
# Helper Function Tests
# ============================================================================


class TestGetClass:
    """Tests for get_class function."""

    def test_returns_list_of_classes(self):
        elem = ET.fromstring('<span class="foo bar baz">text</span>')
        assert parse.get_class(elem) == ["foo", "bar", "baz"]

    def test_returns_single_class_in_list(self):
        elem = ET.fromstring('<span class="single">text</span>')
        assert parse.get_class(elem) == ["single"]

    def test_returns_empty_list_when_no_class_attribute(self):
        elem = ET.fromstring("<span>text</span>")
        # get("class", "").split() returns [] for empty/missing attribute
        assert parse.get_class(elem) == []

    def test_handles_empty_class_attribute(self):
        elem = ET.fromstring('<span class="">text</span>')
        # "".split() returns []
        assert parse.get_class(elem) == []


class TestHasClass:
    """Tests for has_class function."""

    def test_true_when_class_present(self):
        elem = ET.fromstring('<span class="foo bar">text</span>')
        assert parse.has_class(elem, "foo") is True
        assert parse.has_class(elem, "bar") is True

    def test_false_when_class_absent(self):
        elem = ET.fromstring('<span class="foo bar">text</span>')
        assert parse.has_class(elem, "baz") is False

    def test_false_when_no_class_attribute(self):
        elem = ET.fromstring("<span>text</span>")
        assert parse.has_class(elem, "foo") is False


class TestFindByClass:
    """Tests for find_by_class function."""

    def test_finds_all_descendants(self):
        xml = """
        <root>
            <span class="target">1</span>
            <div>
                <span class="target">2</span>
                <span class="other">3</span>
            </div>
        </root>
        """
        elem = ET.fromstring(xml)
        results = parse.find_by_class(elem, "target")
        assert len(results) == 2
        assert all(parse.has_class(r, "target") for r in results)

    def test_direct_only_finds_children(self):
        xml = """
        <root>
            <span class="target">1</span>
            <div>
                <span class="target">2</span>
            </div>
        </root>
        """
        elem = ET.fromstring(xml)
        results = parse.find_by_class(elem, "target", direct_only=True)
        assert len(results) == 1
        assert results[0].text == "1"

    def test_returns_empty_list_when_not_found(self):
        elem = ET.fromstring('<root><span class="other">text</span></root>')
        assert parse.find_by_class(elem, "target") == []


class TestFindFirstByClass:
    """Tests for find_first_by_class function."""

    def test_returns_first_match(self):
        xml = """
        <root>
            <span class="target">first</span>
            <span class="target">second</span>
        </root>
        """
        elem = ET.fromstring(xml)
        result = parse.find_first_by_class(elem, "target")
        assert result is not None
        assert result.text == "first"

    def test_returns_none_when_not_found(self):
        elem = ET.fromstring('<root><span class="other">text</span></root>')
        assert parse.find_first_by_class(elem, "target") is None

    def test_direct_only_finds_first_child(self):
        xml = """
        <root>
            <div><span class="target">nested</span></div>
            <span class="target">direct</span>
        </root>
        """
        elem = ET.fromstring(xml)
        result = parse.find_first_by_class(elem, "target", direct_only=True)
        assert result is not None
        assert result.text == "direct"


class TestGetDirectText:
    """Tests for get_direct_text function."""

    def test_gets_only_direct_text(self):
        xml = '<span>direct <child>nested</child></span>'
        elem = ET.fromstring(xml)
        assert parse.get_direct_text(elem) == "direct"

    def test_ignores_child_text(self):
        xml = '<span><child>nested</child></span>'
        elem = ET.fromstring(xml)
        assert parse.get_direct_text(elem) == ""

    def test_strips_whitespace(self):
        xml = '<span>  text  </span>'
        elem = ET.fromstring(xml)
        assert parse.get_direct_text(elem) == "text"


class TestGetAllText:
    """Tests for get_all_text function."""

    def test_includes_nested_text(self):
        xml = '<span>parent <child>child</child> tail</span>'
        elem = ET.fromstring(xml)
        assert parse.get_all_text(elem) == "parent child tail"

    def test_handles_deeply_nested(self):
        xml = '<a><b><c>deep</c></b></a>'
        elem = ET.fromstring(xml)
        assert parse.get_all_text(elem) == "deep"


class TestNormalizeWhitespace:
    """Tests for normalize_whitespace function."""

    def test_collapses_multiple_spaces(self):
        assert parse.normalize_whitespace("hello   world") == "hello world"

    def test_collapses_tabs_and_newlines(self):
        assert parse.normalize_whitespace("hello\t\nworld") == "hello world"

    def test_trims_leading_trailing(self):
        assert parse.normalize_whitespace("  hello  ") == "hello"

    def test_handles_empty_string(self):
        assert parse.normalize_whitespace("") == ""

    def test_handles_only_whitespace(self):
        assert parse.normalize_whitespace("   \t\n   ") == ""


class TestCleanPunctuation:
    """Tests for clean_punctuation function."""

    def test_removes_space_before_period(self):
        assert parse.clean_punctuation("hello .") == "hello."

    def test_removes_space_before_comma(self):
        assert parse.clean_punctuation("one , two") == "one, two"

    def test_preserves_indentation(self):
        result = parse.clean_punctuation("    indented text .")
        assert result == "    indented text."

    def test_handles_multiline(self):
        text = "line one .\n    line two ."
        result = parse.clean_punctuation(text)
        assert "line one." in result
        assert "line two." in result

    def test_fixes_quotes_with_spaces(self):
        assert "' s" not in parse.clean_punctuation("it' s")


# ============================================================================
# Fraction Formatting Tests
# ============================================================================


class TestFormatFraction:
    """Tests for format_fraction function."""

    def test_unicode_half(self):
        xml = '<span class="frac"><span class="nu">1</span><span class="dn">2</span></span>'
        elem = ET.fromstring(xml)
        assert parse.format_fraction(elem) == "½"

    def test_unicode_third(self):
        xml = '<span class="frac"><span class="nu">1</span><span class="dn">3</span></span>'
        elem = ET.fromstring(xml)
        assert parse.format_fraction(elem) == "⅓"

    def test_unicode_two_thirds(self):
        xml = '<span class="frac"><span class="nu">2</span><span class="dn">3</span></span>'
        elem = ET.fromstring(xml)
        assert parse.format_fraction(elem) == "⅔"

    def test_unicode_quarter(self):
        xml = '<span class="frac"><span class="nu">1</span><span class="dn">4</span></span>'
        elem = ET.fromstring(xml)
        assert parse.format_fraction(elem) == "¼"

    def test_unicode_three_quarters(self):
        xml = '<span class="frac"><span class="nu">3</span><span class="dn">4</span></span>'
        elem = ET.fromstring(xml)
        assert parse.format_fraction(elem) == "¾"

    def test_fallback_superscript_subscript(self):
        # 5/7 doesn't have a unicode character
        xml = '<span class="frac"><span class="nu">5</span><span class="dn">7</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_fraction(elem)
        assert "⁵" in result
        assert "₇" in result

    def test_handles_empty_numerator(self):
        xml = '<span class="frac"><span class="nu"></span><span class="dn">2</span></span>'
        elem = ET.fromstring(xml)
        # Should not raise, returns some form of fraction
        result = parse.format_fraction(elem)
        assert isinstance(result, str)


# ============================================================================
# Inline Content Formatting Tests
# ============================================================================


class TestFormatInlineContent:
    """Tests for format_inline_content function."""

    def test_plain_text(self):
        xml = '<span>plain text</span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "plain text" in result

    def test_bold_class(self):
        xml = '<span><span class="bold">bold text</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "**bold text**" in result

    def test_italic_ex_class(self):
        xml = '<span><span class="ex">example text</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "*example text*" in result

    def test_italic_ge_class(self):
        xml = '<span><span class="ge">glossary text</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "*glossary text*" in result

    def test_italic_sy_class(self):
        xml = '<span><span class="sy">as adjective</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "*as adjective*" in result

    def test_italic_reg_class(self):
        xml = '<span><span class="reg">historical</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "*historical*" in result

    def test_bold_f_class(self):
        xml = '<span><span class="f">word form</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "**word form**" in result

    def test_bold_tx_class(self):
        xml = '<span><span class="tx">Genus species</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "**Genus species**" in result

    def test_bold_ff_class(self):
        xml = '<span><span class="ff">foreign word</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "**foreign word**" in result

    def test_superscript_sup_class(self):
        xml = '<span>x<span class="sup">2</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "²" in result

    def test_subscript_subent_class(self):
        xml = '<span>H<span class="subEnt">2</span>O</span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "₂" in result

    def test_link_with_title(self):
        xml = '<span><a title="target">link text</a></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "[link text](target.md)" in result

    def test_link_with_homograph(self):
        xml = '<span><a title="bow"><span class="ty_hom">1</span>bow</a></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "bow_1.md" in result
        assert "¹" in result

    def test_nested_elements(self):
        xml = '<span><span class="bold">outer <span class="ex">inner</span></span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        # Both formatting should be present
        assert "**" in result

    def test_skips_prn_tags(self):
        xmlns = "http://www.apple.com/DTDs/DictionaryService-1.0.rng"
        xml = f'<span xmlns:d="{xmlns}">text<d:prn>pronunciation</d:prn> after</span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "pronunciation" not in result
        assert "text" in result
        assert "after" in result

    def test_fraction_inside_content(self):
        xml = '<span>about <span class="frac"><span class="nu">1</span><span class="dn">2</span></span> cup</span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "½" in result

    def test_lbl_class(self):
        xml = '<span><span class="lbl">[with object]</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "[with object]" in result

    def test_gg_class(self):
        xml = '<span><span class="gg">[no object]</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "[no object]" in result


# ============================================================================
# Section Formatting Tests
# ============================================================================


class TestFormatHeader:
    """Tests for format_header function."""

    def test_with_word_and_pronunciation(self, simple_entry_element):
        result = parse.format_header(simple_entry_element)
        assert "# test" in result
        assert "|test|" in result

    def test_with_homograph(self, homograph_entry_element):
        result = parse.format_header(homograph_entry_element)
        assert "# bow" in result
        assert "¹" in result  # Superscript 1

    def test_missing_pronunciation(self):
        xml = """
        <d:entry xmlns:d="http://www.apple.com/DTDs/DictionaryService-1.0.rng" d:title="word">
            <span class="hg"><span class="hw">word</span></span>
        </d:entry>
        """
        elem = ET.fromstring(xml)
        result = parse.format_header(elem)
        assert "# word" in result


class TestFormatExampleGroup:
    """Tests for format_example_group function."""

    def test_formats_example(self):
        xml = '<span class="eg"><span class="ex">an example sentence</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_example_group(elem)
        assert "*an example sentence*" in result


class TestFormatDefinitionBlock:
    """Tests for format_definition_block function."""

    def test_with_definition_and_example(self):
        xml = """
        <span class="msDict">
            <span class="df">the main definition</span>
            <span class="eg"><span class="ex">example usage</span></span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_definition_block(elem)
        assert "the main definition" in result


class TestFormatSense:
    """Tests for format_sense function."""

    def test_numbered_sense(self):
        xml = """
        <span class="se2">
            <span class="sn">1</span>
            <span class="msDict">
                <span class="df">first definition</span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_sense(elem)
        assert "1 " in result
        assert "first definition" in result

    def test_bullet_sense(self):
        xml = """
        <span class="se2">
            <span class="sn">•</span>
            <span class="msDict">
                <span class="df">bullet definition</span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_sense(elem)
        assert "  - " in result


class TestFormatSubsense:
    """Tests for format_subsense function."""

    def test_subsense_with_label(self):
        xml = """
        <span class="msDict t_subsense">
            <span class="lg"><span class="reg">historical</span></span>
            <span class="df">historical meaning</span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_subsense(elem)
        assert "  - " in result
        assert "*historical*" in result


class TestFormatPosBlock:
    """Tests for format_pos_block function."""

    def test_with_grammar(self):
        xml = """
        <span class="se1">
            <span class="pos">verb</span>
            <span class="gg">[with object]</span>
            <span class="msDict">
                <span class="df">to do something</span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_pos_block(elem)
        assert "**verb**" in result
        assert "[with object]" in result

    def test_with_subject(self):
        xml = """
        <span class="se1">
            <span class="pos">noun</span>
            <span class="sj">Astronomy</span>
            <span class="msDict">
                <span class="df">a celestial body</span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_pos_block(elem)
        assert "**noun**" in result
        assert "*Astronomy*" in result


class TestFormatPhrasesSection:
    """Tests for format_phrases_section function."""

    def test_formats_phrases(self):
        xml = """
        <span class="subEntryBlock t_phrases">
            <span class="subEntry">
                <span class="l">a phrase</span>
                <span class="msDict">
                    <span class="df">phrase meaning</span>
                </span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_phrases_section(elem)
        assert "## PHRASES" in result
        assert "**a phrase**" in result
        assert "phrase meaning" in result


class TestFormatDerivativesSection:
    """Tests for format_derivatives_section function."""

    def test_formats_derivatives(self):
        xml = """
        <span class="subEntryBlock t_derivatives">
            <span class="subEntry">
                <span class="l">derivation</span>
                <span class="pr">|ˌderəˈvāSH(ə)n|</span>
                <span class="pos">noun</span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_derivatives_section(elem)
        assert "## DERIVATIVES" in result
        assert "**derivation**" in result
        assert "noun" in result


class TestFormatOriginSection:
    """Tests for format_origin_section function."""

    def test_formats_origin(self):
        xml = """
        <span class="etym">
            <span class="x_xoh">ORIGIN</span>
            <span class="x_xo1">Old English <span class="ff">word</span>, from Latin.</span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_origin_section(elem)
        assert "## ORIGIN" in result
        assert "Old English" in result
        assert "**word**" in result


class TestFormatNote:
    """Tests for format_note function."""

    def test_with_label(self):
        xml = """
        <span class="note">
            <span class="lbl">USAGE</span>
            This is a usage note.
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_note(elem)
        assert "> " in result
        assert "**USAGE**" in result

    def test_without_label(self):
        xml = '<span class="note">Just a note.</span>'
        elem = ET.fromstring(xml)
        result = parse.format_note(elem)
        assert "> " in result
        assert "Just a note." in result


# ============================================================================
# Integration Tests
# ============================================================================


class TestXmlToMarkdown:
    """Tests for xml_to_markdown function."""

    def test_simple_entry(self, simple_entry_element):
        result = parse.xml_to_markdown(simple_entry_element)
        assert "# test" in result
        assert "**noun**" in result
        assert "procedure" in result

    def test_complex_entry(self, complex_entry_element):
        result = parse.xml_to_markdown(complex_entry_element)
        assert "# run" in result
        assert "**verb**" in result
        assert "## PHRASES" in result
        assert "## DERIVATIVES" in result
        assert "## ORIGIN" in result
        assert "> **USAGE**" in result

    def test_with_all_sections(self, complex_entry_element):
        result = parse.xml_to_markdown(complex_entry_element)
        # Verify structure
        lines = result.split("\n")
        headers = [l for l in lines if l.startswith("#")]
        assert len(headers) >= 4  # Main header + sections

    def test_with_fractions(self, fraction_entry_element):
        result = parse.xml_to_markdown(fraction_entry_element)
        assert "½" in result


class TestProcessFile:
    """Tests for process_file function."""

    def test_creates_md_file(self, temp_xml_file: Path):
        md_path = parse.process_file(temp_xml_file)
        assert md_path.exists()
        assert md_path.suffix == ".md"
        content = md_path.read_text()
        assert "# test" in content

    def test_md_file_has_correct_name(self, temp_xml_file: Path):
        md_path = parse.process_file(temp_xml_file)
        assert md_path.name == "test_entry.md"


class TestTrackElement:
    """Tests for track_element function."""

    def test_records_unhandled_tag(self):
        # Clear any existing tracking
        parse.unhandled_tags.clear()
        parse.unhandled_classes.clear()

        xml = '<custom_tag class="unknown_class">text</custom_tag>'
        elem = ET.fromstring(xml)
        parse.track_element(elem)

        assert "custom_tag" in parse.unhandled_tags
        assert "unknown_class" in parse.unhandled_classes

    def test_ignores_known_tags(self):
        parse.unhandled_tags.clear()
        xml = '<span class="hg">text</span>'
        elem = ET.fromstring(xml)
        parse.track_element(elem)
        assert "span" not in parse.unhandled_tags

    def test_ignores_handled_classes(self):
        parse.unhandled_classes.clear()
        xml = '<span class="hw">text</span>'
        elem = ET.fromstring(xml)
        parse.track_element(elem)
        assert "hw" not in parse.unhandled_classes


class TestReportUnhandled:
    """Tests for report_unhandled function."""

    def test_reports_unhandled(self):
        parse.unhandled_tags.clear()
        parse.unhandled_classes.clear()
        parse.unhandled_tags["test_tag"] = ("file.xml", "<test_tag/>")
        parse.unhandled_classes["test_class"] = ("file.xml", "<span/>")

        report = parse.report_unhandled()
        assert "test_tag" in report
        assert "test_class" in report

    def test_all_handled_message(self):
        parse.unhandled_tags.clear()
        parse.unhandled_classes.clear()
        report = parse.report_unhandled()
        assert "All patterns handled" in report
