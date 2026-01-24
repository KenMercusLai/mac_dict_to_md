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


class TestGetPronunciationText:
    """Tests for get_pronunciation_text function."""

    def test_skips_respell_by_default(self):
        """By default (IPA mode), t_respell content should be skipped."""
        parse._use_respell = False
        xml = '''
        <prx>
            <span class="ph t_IPA">ˈɑksfərd</span>
            <span class="ph t_respell">AHK-sferd</span>
        </prx>
        '''
        elem = ET.fromstring(xml)
        result = parse.get_pronunciation_text(elem)
        assert "ˈɑksfərd" in result
        assert "AHK-sferd" not in result

    def test_skips_ipa_when_respell_enabled(self):
        """When --respell is used, t_IPA content should be skipped."""
        parse._use_respell = True
        xml = '''
        <prx>
            <span class="ph t_IPA">ˈɑksfərd</span>
            <span class="ph t_respell">AHK-sferd</span>
        </prx>
        '''
        elem = ET.fromstring(xml)
        result = parse.get_pronunciation_text(elem)
        assert "ˈɑksfərd" not in result
        assert "AHK-sferd" in result
        # Reset for other tests
        parse._use_respell = False

    def test_handles_nested_structure(self):
        """Should handle pronunciation with nested elements."""
        parse._use_respell = False
        xml = '''
        <prx>
            <span class="ph t_IPA" dialect="AmE">
                ˈɑksfərd
            </span>
            <span class="ph t_respell">
                AHK-sferd
            </span>
        </prx>
        '''
        elem = ET.fromstring(xml)
        result = parse.get_pronunciation_text(elem)
        assert "ˈɑksfərd" in result
        assert "AHK-sferd" not in result

    def test_preserves_tail_text(self):
        """Tail text after skipped elements should be preserved."""
        parse._use_respell = False
        xml = '''
        <prx>|<span class="ph t_IPA">ˈɑksfərd</span>|<span class="ph t_respell">AHK</span>|</prx>
        '''
        elem = ET.fromstring(xml)
        result = parse.get_pronunciation_text(elem)
        # Should have | before and after IPA, and | after skipped respell
        assert "|ˈɑksfərd|" in result
        assert "AHK" not in result

    def test_handles_only_ipa(self):
        """Should work when only IPA is present."""
        parse._use_respell = False
        xml = '<prx><span class="ph t_IPA">ˈɑksfərd</span></prx>'
        elem = ET.fromstring(xml)
        result = parse.get_pronunciation_text(elem)
        assert "ˈɑksfərd" in result

    def test_handles_only_respell(self):
        """Should work when only respell is present."""
        parse._use_respell = True
        xml = '<prx><span class="ph t_respell">AHK-sferd</span></prx>'
        elem = ET.fromstring(xml)
        result = parse.get_pronunciation_text(elem)
        assert "AHK-sferd" in result
        parse._use_respell = False


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

    def test_ty_hom_converts_to_superscript(self):
        """Test that ty_hom class converts numbers to superscript."""
        xml = '<span><span class="gp ty_hom tg_xr">2</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "²" in result

    def test_ty_hom_strips_surrounding_whitespace(self):
        """Test that ty_hom strips whitespace around the number."""
        xml = '<span>word <span class="ty_hom"> 1 </span> more</span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "word¹" in result

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

    def test_x_blk_occupies_own_line(self):
        """Test that x_blk class causes content to occupy its own line."""
        xml = '<span><span class="lbl x_blk">USAGE</span> Some note text.</span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "USAGE\n" in result
        assert "Some note text." in result

    def test_x_blk_with_bold_content(self):
        """Test x_blk works with subsequent bold elements."""
        xml = '<span><span class="x_blk">Header</span><span class="bold">Bold text</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "Header\n" in result
        assert "**Bold text**" in result

    def test_x_blk_standalone(self):
        """Test x_blk element alone."""
        xml = '<span><span class="x_blk">Standalone</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "Standalone\n" in result

    def test_xr_class_ignored_preserves_content(self):
        """Test that xr class is ignored but content is preserved."""
        xml = '<span>before <span class="xr">cross reference</span> after</span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "cross reference" in result
        assert "before" in result
        assert "after" in result

    def test_xr_class_no_special_formatting(self):
        """Test that xr class does not apply any special formatting."""
        xml = '<span><span class="xr">plain text</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert result.strip() == "plain text"
        assert "**" not in result
        assert "*plain text*" not in result

    def test_xr_with_nested_content(self):
        """Test xr with nested formatted content."""
        xml = '<span><span class="xr">see <span class="bold">other</span></span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "see" in result
        assert "**other**" in result

    def test_xrg_class_ignored_preserves_content(self):
        """Test that xrg (cross-reference group) class is ignored but content is preserved."""
        xml = '<span>from <span class="xrg"><span class="xr"><a title="million">million</a></span></span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "from" in result
        assert "million" in result

    def test_xrg_class_no_special_formatting(self):
        """Test that xrg class does not apply any special formatting."""
        xml = '<span><span class="xrg">plain text</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert result.strip() == "plain text"
        assert "**" not in result
        assert "*plain text*" not in result

    def test_xrlabelGroup_class_ignored_preserves_content(self):
        """Test that xrlabelGroup class is ignored but content is preserved."""
        xml = '<span>before <span class="xrlabelGroup">label group</span> after</span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "label group" in result
        assert "before" in result
        assert "after" in result

    def test_xrlabelGroup_class_no_special_formatting(self):
        """Test that xrlabelGroup class does not apply any special formatting."""
        xml = '<span><span class="xrlabelGroup">plain text</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert result.strip() == "plain text"
        assert "**" not in result
        assert "*plain text*" not in result

    def test_xrlabel_class_ignored_preserves_content(self):
        """Test that xrlabel class is ignored but content is preserved."""
        xml = '<span>before <span class="xrlabel">label</span> after</span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "label" in result
        assert "before" in result
        assert "after" in result

    def test_xrlabel_class_no_special_formatting(self):
        """Test that xrlabel class does not apply any special formatting."""
        xml = '<span><span class="xrlabel">plain text</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert result.strip() == "plain text"
        assert "**" not in result
        assert "*plain text*" not in result

    def test_vg_class_preserves_content(self):
        """Test that vg (variant group) class preserves its content with bold variant."""
        xml = '<span><span class="vg">(also <span class="v">slumberous</span>)</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "(also **slumberous**)" in result

    def test_v_class_formats_bold(self):
        """Test that v (variant) class formats content as bold."""
        xml = '<span><span class="v">variant</span></span>'
        elem = ET.fromstring(xml)
        result = parse.format_inline_content(elem)
        assert "**variant**" in result


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

    def test_cross_reference_sense(self):
        """Test sense with xrg (cross-reference) instead of df (definition)."""
        xml = """
        <span class="se2">
            <span class="sn">2</span>
            <span class="msDict">
                <span class="xrg">
                    another term for
                    <span class="xr">
                        <a title="macule">macule</a>
                    </span>
                </span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_sense(elem)
        assert "2 " in result
        assert "another term for" in result
        assert "[macule](macule.md)" in result


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

    def test_definition_with_colon_and_examples_inline(self):
        """Test that definition, punctuation, and examples are on same line."""
        xml = """
        <span class="se1">
            <span class="pos">symbol</span>
            <span class="msDict">
                <span class="df">the pound sign</span>
                <span class="gp tg_df">:</span>
                <span class="eg">
                    <span class="ex">example one</span>
                    <span class="gp tg_eg">|</span>
                </span>
                <span class="eg">
                    <span class="ex">example two</span>
                    <span class="gp tg_eg">.</span>
                </span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_pos_block(elem)
        lines = [line for line in result.split("\n") if line.strip()]
        # Find the line with the definition
        def_line = next((line for line in lines if "pound sign" in line), None)
        assert def_line is not None
        # All content should be on same line
        assert ":" in def_line
        assert "*example one*" in def_line
        assert "*example two*" in def_line

    def test_with_inflection_group(self):
        """Test that inflection group (plural form) is included after POS."""
        xml = """
        <span class="se1">
            <span class="posg">
                <span class="pos">noun</span>
                <span class="infg">
                    <span class="gp tg_infg">(</span>
                    <span class="sy">plural</span>
                    <span class="inf">maculae</span>
                    <span class="prx">| ˈmækjəˌli |</span>
                    <span class="gp tg_infg">)</span>
                </span>
            </span>
            <span class="msDict">
                <span class="df">a spot or mark</span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_pos_block(elem)
        # POS line should include noun and the inflection group
        assert "**noun**" in result
        assert "*plural*" in result
        assert "maculae" in result
        assert "ˈmækjəˌli" in result
        # Should have opening/closing parens
        assert "(" in result
        assert ")" in result

    def test_with_inflection_group_no_pronunciation(self):
        """Test inflection group without pronunciation."""
        xml = """
        <span class="se1">
            <span class="posg">
                <span class="pos">noun</span>
                <span class="infg">
                    <span class="gp tg_infg">(</span>
                    <span class="sy">plural</span>
                    <span class="inf">cacti</span>
                    <span class="gp tg_infg">)</span>
                </span>
            </span>
            <span class="msDict">
                <span class="df">a succulent plant</span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_pos_block(elem)
        assert "**noun**" in result
        assert "*plural*" in result
        assert "cacti" in result


class TestFormatSubentryContent:
    """Tests for format_subentry_content function."""

    def test_simple_msdict(self):
        xml = """
        <span class="subEntry">
            <span class="l">a phrase</span>
            <span class="msDict">
                <span class="df">phrase meaning</span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_subentry_content(elem)
        assert len(result) == 1
        assert "phrase meaning" in result[0]

    def test_with_se2_numbered_senses(self):
        xml = """
        <span class="subEntry">
            <span class="l">settle accounts</span>
            <span class="se2">
                <span class="sn">1</span>
                <span class="msDict">
                    <span class="df">have revenge on</span>
                </span>
            </span>
            <span class="se2">
                <span class="sn">2</span>
                <span class="msDict">
                    <span class="df">pay money owed</span>
                </span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_subentry_content(elem)
        assert len(result) == 2
        assert "1 have revenge on" in result[0]
        assert "2 pay money owed" in result[1]

    def test_with_subsenses(self):
        xml = """
        <span class="subEntry">
            <span class="l">on one's own account</span>
            <span class="msDict">
                <span class="df">for one's own purposes</span>
            </span>
            <span class="msDict t_subsense">
                <span class="df">alone; unaided</span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_subentry_content(elem)
        assert len(result) == 2
        assert "for one's own purposes" in result[0]
        assert "  - alone; unaided" in result[1]


class TestFormatSubentrySense:
    """Tests for format_subentry_sense function."""

    def test_numbered_sense_with_definition(self):
        xml = """
        <span class="se2">
            <span class="sn">1</span>
            <span class="msDict">
                <span class="df">first meaning</span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_subentry_sense(elem)
        assert len(result) == 1
        assert "1 first meaning" in result[0]

    def test_with_form_group(self):
        xml = """
        <span class="se2">
            <span class="x_xoh">
                <span class="tg_se2">1</span>
                <span class="fg">( <span class="f">account for something</span> )</span>
            </span>
            <span class="msDict">
                <span class="df">give a satisfactory record</span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_subentry_sense(elem)
        assert len(result) == 1
        assert "1" in result[0]
        assert "account for something" in result[0]
        assert "give a satisfactory record" in result[0]

    def test_with_subsenses(self):
        xml = """
        <span class="se2">
            <span class="sn">1</span>
            <span class="msDict">
                <span class="df">main meaning</span>
            </span>
            <span class="msDict t_subsense">
                <span class="df">sub meaning one</span>
            </span>
            <span class="msDict t_subsense">
                <span class="df">sub meaning two</span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_subentry_sense(elem)
        assert len(result) == 3
        assert "1 main meaning" in result[0]
        assert "  - sub meaning one" in result[1]
        assert "  - sub meaning two" in result[2]


class TestFormatSubentryMsdict:
    """Tests for format_subentry_msdict function."""

    def test_simple_definition(self):
        xml = """
        <span class="msDict">
            <span class="df">a definition</span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_subentry_msdict(elem, is_subsense=False)
        assert result == "a definition"

    def test_subsense_has_bullet_prefix(self):
        xml = """
        <span class="msDict t_subsense">
            <span class="df">a subsense</span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_subentry_msdict(elem, is_subsense=True)
        assert result == "  - a subsense"

    def test_with_form_group(self):
        xml = """
        <span class="msDict">
            <span class="fg">( <span class="f">account for someone</span> )</span>
            <span class="df">know the whereabouts</span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_subentry_msdict(elem, is_subsense=False)
        assert "account for someone" in result
        assert "know the whereabouts" in result

    def test_with_label_group(self):
        xml = """
        <span class="msDict">
            <span class="lg"><span class="reg">archaic</span></span>
            <span class="df">an old meaning</span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_subentry_msdict(elem, is_subsense=False)
        assert "archaic" in result
        assert "an old meaning" in result

    def test_with_example(self):
        xml = """
        <span class="msDict">
            <span class="df">a definition</span>
            <span class="eg"><span class="ex">an example sentence</span></span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_subentry_msdict(elem, is_subsense=False)
        assert "a definition" in result
        assert "an example sentence" in result


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

    def test_formats_phrase_with_numbered_senses(self):
        xml = """
        <span class="subEntryBlock t_phrases">
            <span class="subEntry">
                <span class="l">settle accounts with</span>
                <span class="se2">
                    <span class="sn">1</span>
                    <span class="msDict">
                        <span class="df">have revenge on</span>
                    </span>
                </span>
                <span class="se2">
                    <span class="sn">2</span>
                    <span class="msDict">
                        <span class="df">pay money owed to (someone)</span>
                    </span>
                </span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_phrases_section(elem)
        assert "**settle accounts with**" in result
        assert "1 have revenge on" in result
        assert "2 pay money owed to (someone)" in result

    def test_formats_phrase_with_subsenses(self):
        xml = """
        <span class="subEntryBlock t_phrases">
            <span class="subEntry">
                <span class="l">on one's own account</span>
                <span class="msDict">
                    <span class="df">for one's own purposes; for oneself</span>
                </span>
                <span class="msDict t_subsense">
                    <span class="df">alone; unaided</span>
                </span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_phrases_section(elem)
        assert "**on one's own account**" in result
        assert "for one's own purposes; for oneself" in result
        assert "  - alone; unaided" in result

    def test_formats_phrase_with_variant_group(self):
        """Test phrase with variant form (vg class) in x_xoh."""
        xml = """
        <span class="subEntryBlock t_phrases">
            <span class="subEntry">
                <span class="x_xoh">
                    <span class="l">tear someone a new arsehole</span>
                    <span class="vg">(also <span class="v">rip someone a new arsehole</span>)</span>
                </span>
                <span class="msDict">
                    <span class="df">criticize someone severely</span>
                </span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_phrases_section(elem)
        assert "**tear someone a new arsehole**" in result
        assert "(also **rip someone a new arsehole**)" in result
        assert "criticize someone severely" in result

    def test_formats_phrase_without_variant_still_works(self):
        """Test that phrases without variant groups still work correctly."""
        xml = """
        <span class="subEntryBlock t_phrases">
            <span class="subEntry">
                <span class="x_xoh">
                    <span class="l">a simple phrase</span>
                </span>
                <span class="msDict">
                    <span class="df">a simple definition</span>
                </span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_phrases_section(elem)
        assert "**a simple phrase**" in result
        assert "a simple definition" in result


class TestFormatPhrasalVerbsSection:
    """Tests for format_phrasal_verbs_section function."""

    def test_formats_phrasal_verbs(self):
        xml = """
        <span class="subEntryBlock t_phrasalVerbs">
            <span class="subEntry">
                <span class="l">get along</span>
                <span class="msDict">
                    <span class="df">have a harmonious relationship</span>
                </span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_phrasal_verbs_section(elem)
        assert "## PHRASAL VERBS" in result
        assert "**get along**" in result
        assert "have a harmonious relationship" in result

    def test_formats_multiple_phrasal_verbs(self):
        xml = """
        <span class="subEntryBlock t_phrasalVerbs">
            <span class="subEntry">
                <span class="l">get along</span>
                <span class="msDict">
                    <span class="df">have a harmonious relationship</span>
                </span>
            </span>
            <span class="subEntry">
                <span class="l">get away</span>
                <span class="msDict">
                    <span class="df">escape from a place</span>
                </span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_phrasal_verbs_section(elem)
        assert "**get along**" in result
        assert "**get away**" in result

    def test_formats_phrasal_verbs_with_examples(self):
        xml = """
        <span class="subEntryBlock t_phrasalVerbs">
            <span class="subEntry">
                <span class="l">get by</span>
                <span class="msDict">
                    <span class="df">manage with difficulty</span>
                    <span class="eg"><span class="ex">we can just about get by</span></span>
                </span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_phrasal_verbs_section(elem)
        assert "**get by**" in result
        assert "manage with difficulty" in result

    def test_section_has_horizontal_rule(self):
        xml = """
        <span class="subEntryBlock t_phrasalVerbs">
            <span class="subEntry">
                <span class="l">get along</span>
                <span class="msDict">
                    <span class="df">have a harmonious relationship</span>
                </span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_phrasal_verbs_section(elem)
        assert result.startswith("---")

    def test_formats_phrasal_verb_with_numbered_senses(self):
        xml = """
        <span class="subEntryBlock t_phrasalVerbs">
            <span class="subEntry">
                <span class="l">account for</span>
                <span class="se2">
                    <span class="sn">1</span>
                    <span class="msDict">
                        <span class="df">give a satisfactory record</span>
                    </span>
                </span>
                <span class="se2">
                    <span class="sn">2</span>
                    <span class="msDict">
                        <span class="df">succeed in killing or defeating</span>
                    </span>
                </span>
                <span class="se2">
                    <span class="sn">3</span>
                    <span class="msDict">
                        <span class="df">supply or make up a specified amount</span>
                    </span>
                </span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_phrasal_verbs_section(elem)
        assert "**account for**" in result
        assert "1 give a satisfactory record" in result
        assert "2 succeed in killing or defeating" in result
        assert "3 supply or make up a specified amount" in result

    def test_formats_phrasal_verb_with_subsenses(self):
        xml = """
        <span class="subEntryBlock t_phrasalVerbs">
            <span class="subEntry">
                <span class="l">account for</span>
                <span class="se2">
                    <span class="sn">1</span>
                    <span class="msDict">
                        <span class="df">give a satisfactory record</span>
                    </span>
                    <span class="msDict t_subsense">
                        <span class="df">provide an explanation or reason</span>
                    </span>
                    <span class="msDict t_subsense">
                        <span class="df">know the whereabouts of someone</span>
                    </span>
                </span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_phrasal_verbs_section(elem)
        assert "**account for**" in result
        assert "1 give a satisfactory record" in result
        assert "  - provide an explanation or reason" in result
        assert "  - know the whereabouts of someone" in result

    def test_formats_phrasal_verb_with_form_group(self):
        xml = """
        <span class="subEntryBlock t_phrasalVerbs">
            <span class="subEntry">
                <span class="l">account for</span>
                <span class="se2">
                    <span class="x_xoh">
                        <span class="tg_se2">1</span>
                        <span class="fg">( <span class="f">account for something</span> )</span>
                    </span>
                    <span class="msDict">
                        <span class="df">give a satisfactory record</span>
                    </span>
                </span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_phrasal_verbs_section(elem)
        assert "**account for**" in result
        assert "account for something" in result
        assert "give a satisfactory record" in result

    def test_formats_phrasal_verb_with_variant_group(self):
        """Test phrasal verb with variant form (vg class) in x_xoh."""
        xml = """
        <span class="subEntryBlock t_phrasalVerbs">
            <span class="subEntry">
                <span class="x_xoh">
                    <span class="l">get along</span>
                    <span class="vg">(also <span class="v">get on</span>)</span>
                </span>
                <span class="msDict">
                    <span class="df">have a harmonious relationship</span>
                </span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_phrasal_verbs_section(elem)
        assert "**get along**" in result
        assert "(also **get on**)" in result
        assert "have a harmonious relationship" in result


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

    def test_formats_derivative_with_variant_group(self):
        """Test derivative with variant form (vg class) in x_xoh."""
        xml = """
        <span class="subEntryBlock t_derivatives">
            <span class="subEntry">
                <span class="x_xoh">
                    <span class="l">slumbrous</span>
                    <span class="pr">|ˈsləmbərəs|</span>
                    <span class="vg">(<span class="v">slumberous</span>)</span>
                </span>
                <span class="pos">adjective</span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_derivatives_section(elem)
        assert "**slumbrous**" in result
        assert "|ˈsləmbərəs|" in result
        assert "(**slumberous**)" in result
        assert "adjective" in result

    def test_formats_derivative_without_variant_still_works(self):
        """Test that derivatives without variant groups still work correctly."""
        xml = """
        <span class="subEntryBlock t_derivatives">
            <span class="subEntry">
                <span class="x_xoh">
                    <span class="l">simple</span>
                    <span class="pr">|ˈsimpəl|</span>
                </span>
                <span class="pos">adjective</span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_derivatives_section(elem)
        assert "**simple**" in result
        assert "|ˈsimpəl|" in result
        assert "adjective" in result

    def test_formats_derivative_with_prx_pronunciation(self):
        """Test derivative with prx class pronunciation."""
        xml = """
        <span class="subEntryBlock t_derivatives">
            <span class="subEntry">
                <span class="l">derivation</span>
                <span class="prx">|ˌderəˈvāSH(ə)n|</span>
                <span class="pos">noun</span>
            </span>
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_derivatives_section(elem)
        assert "**derivation**" in result
        assert "|ˌderəˈvāSH(ə)n|" in result
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

    def test_with_x_blk_label(self):
        """Test note with lbl x_blk class - content on separate lines."""
        xml = """
        <span class="note">
            <span class="lbl x_blk">USAGE</span>
            This is a usage note.
        </span>
        """
        elem = ET.fromstring(xml)
        result = parse.format_note(elem)
        # Should have two blockquote lines
        lines = result.split("\n")
        assert len(lines) == 2
        assert lines[0] == "> **USAGE**"
        assert lines[1].startswith("> ")
        assert "This is a usage note." in lines[1]


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

    def test_with_phrasal_verbs(self, phrasal_verbs_entry_element):
        result = parse.xml_to_markdown(phrasal_verbs_entry_element)
        assert "# get" in result
        assert "## PHRASAL VERBS" in result
        assert "**get along**" in result
        assert "have a harmonious relationship" in result
        assert "**get away**" in result
        assert "**get by**" in result


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

    def test_xr_class_is_handled(self):
        """Test that xr class is recognized as handled."""
        parse.unhandled_classes.clear()
        xml = '<span class="xr">cross reference</span>'
        elem = ET.fromstring(xml)
        parse.track_element(elem)
        assert "xr" not in parse.unhandled_classes

    def test_xrg_class_is_handled(self):
        """Test that xrg class is recognized as handled."""
        parse.unhandled_classes.clear()
        xml = '<span class="xrg">cross reference group</span>'
        elem = ET.fromstring(xml)
        parse.track_element(elem)
        assert "xrg" not in parse.unhandled_classes

    def test_xrlabelGroup_class_is_handled(self):
        """Test that xrlabelGroup class is recognized as handled."""
        parse.unhandled_classes.clear()
        xml = '<span class="xrlabelGroup">label group</span>'
        elem = ET.fromstring(xml)
        parse.track_element(elem)
        assert "xrlabelGroup" not in parse.unhandled_classes

    def test_xrlabel_class_is_handled(self):
        """Test that xrlabel class is recognized as handled."""
        parse.unhandled_classes.clear()
        xml = '<span class="xrlabel">label</span>'
        elem = ET.fromstring(xml)
        parse.track_element(elem)
        assert "xrlabel" not in parse.unhandled_classes

    def test_v_class_is_handled(self):
        """Test that v (variant word) class is recognized as handled."""
        parse.unhandled_classes.clear()
        xml = '<span class="v">slumberous</span>'
        elem = ET.fromstring(xml)
        parse.track_element(elem)
        assert "v" not in parse.unhandled_classes

    def test_vg_class_is_handled(self):
        """Test that vg (variant group) class is recognized as handled."""
        parse.unhandled_classes.clear()
        xml = '<span class="vg">(also slumberous)</span>'
        elem = ET.fromstring(xml)
        parse.track_element(elem)
        assert "vg" not in parse.unhandled_classes

    def test_infg_class_is_handled(self):
        """Test that infg (inflection group) class is recognized as handled."""
        parse.unhandled_classes.clear()
        xml = '<span class="infg">(plural maculae)</span>'
        elem = ET.fromstring(xml)
        parse.track_element(elem)
        assert "infg" not in parse.unhandled_classes

    def test_inf_class_is_handled(self):
        """Test that inf (inflected form) class is recognized as handled."""
        parse.unhandled_classes.clear()
        xml = '<span class="inf">maculae</span>'
        elem = ET.fromstring(xml)
        parse.track_element(elem)
        assert "inf" not in parse.unhandled_classes


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
