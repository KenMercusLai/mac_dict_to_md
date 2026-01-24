#!/usr/bin/env python3
"""
Parses dictionary XML files into Markdown format.

Converts split dictionary XML entries into readable Markdown files
that closely match the visual rendering of the macOS Dictionary app.
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterator
from xml.etree.ElementTree import Element

# Tracking for unhandled patterns with examples: pattern -> (source_file, xml_snippet)
unhandled_tags: dict[str, tuple[str, str]] = {}
unhandled_classes: dict[str, tuple[str, str]] = {}

# Current source file being processed (for tracking)
_current_source_file: str = ""

# Known tags that we handle
KNOWN_TAGS = {
    "a",
    "span",
    "d:entry",
    "d:def",
    "d:pos",
    "d:prn",
    "{http://www.apple.com/DTDs/DictionaryService-1.0.rng}entry",
    "{http://www.apple.com/DTDs/DictionaryService-1.0.rng}def",
    "{http://www.apple.com/DTDs/DictionaryService-1.0.rng}pos",
    "{http://www.apple.com/DTDs/DictionaryService-1.0.rng}prn",
}

# Classes that have explicit formatting rules
HANDLED_CLASSES = {
    # Header
    "hg",
    "hw",
    "prx",
    "ph",
    "gp",
    "hsb",
    "syl_txt",
    # Structure
    "sg",
    "se1",
    "se2",
    "msDict",
    "posg",
    "pos",
    "gg",
    "x_xdh",
    # Content
    "df",
    "eg",
    "ex",
    "f",
    "fg",
    "ge",
    "lg",
    "reg",
    "bold",
    "l",
    "lbl",
    "sn",
    "sj",
    "work",
    "tx",
    "q",
    "sy",
    "subEnt",
    "sup",
    # Fractions
    "frac",
    "nu",
    "dn",
    # Sections
    "subEntryBlock",
    "subEntry",
    "etym",
    "note",
    "dg",
    "date",
    "la",
    "ff",
    "trans",
    "pr",
    # Markers (prefixes we recognize)
    "t_respell",
    "t_IPA",
    "t_first",
    "t_subsense",
    "t_core",
    "t_phrases",
    "t_phrasalVerbs",
    "t_derivatives",
    "ty_label",
    "x_xh0",
    "x_xd0",
    "x_xd1",
    "x_xd1sub",
    "x_xdh",
    "x_xdt",
    "x_xo0",
    "x_xo1",
    "x_xo2",
    "x_xoh",
    "x_xoLblBlk",
    "hasSn",
    "entry",
    "x_blk",
    "xr",
    "xrg",
    "xrlabelGroup",
    "xrlabel",
    "v",     # variant word (inside vg)
    "vg",    # variant group
}

# Superscript mapping for homograph numbers and fractions
SUPERSCRIPT = {
    "0": "⁰",
    "1": "¹",
    "2": "²",
    "3": "³",
    "4": "⁴",
    "5": "⁵",
    "6": "⁶",
    "7": "⁷",
    "8": "⁸",
    "9": "⁹",
}

# Subscript mapping for fraction denominators
SUBSCRIPT = {
    "0": "₀",
    "1": "₁",
    "2": "₂",
    "3": "₃",
    "4": "₄",
    "5": "₅",
    "6": "₆",
    "7": "₇",
    "8": "₈",
    "9": "₉",
}

# Unicode fraction mapping: (numerator, denominator) -> unicode char
UNICODE_FRACTIONS: dict[tuple[int, int], str] = {
    (1, 2): "½",
    (1, 3): "⅓",
    (2, 3): "⅔",
    (1, 4): "¼",
    (3, 4): "¾",
    (1, 5): "⅕",
    (2, 5): "⅖",
    (3, 5): "⅗",
    (4, 5): "⅘",
    (1, 6): "⅙",
    (5, 6): "⅚",
    (1, 7): "⅐",
    (1, 8): "⅛",
    (3, 8): "⅜",
    (5, 8): "⅝",
    (7, 8): "⅞",
    (1, 9): "⅑",
    (1, 10): "⅒",
}


def get_class(elem: Element) -> list[str]:
    """Get CSS classes from element's class attribute."""
    return elem.get("class", "").split()


def has_class(elem: Element, cls: str) -> bool:
    """Check if element has a specific class."""
    return cls in get_class(elem)


def find_by_class(elem: Element, cls: str, direct_only: bool = False) -> list[Element]:
    """Find elements with a specific class."""
    if direct_only:
        return [e for e in elem if has_class(e, cls)]
    return [e for e in elem.iter() if has_class(e, cls)]


def find_first_by_class(elem: Element, cls: str, direct_only: bool = False) -> Element | None:
    """Find first element with a specific class."""
    if direct_only:
        for e in elem:
            if has_class(e, cls):
                return e
        return None
    for e in elem.iter():
        if has_class(e, cls):
            return e
    return None


def get_direct_text(elem: Element) -> str:
    """Get only the direct text of an element, not from children."""
    return (elem.text or "").strip()


def get_all_text(elem: Element) -> str:
    """Recursively get all text content from element and children."""
    return "".join(elem.itertext()).strip()


def normalize_whitespace(text: str) -> str:
    """Collapse multiple whitespaces into single spaces."""
    return " ".join(text.split())


def clean_punctuation(text: str) -> str:
    """Clean up whitespace around punctuation, preserving line breaks and indentation."""
    import re

    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        # Preserve leading whitespace (indentation)
        leading = len(line) - len(line.lstrip())
        indent = line[:leading]
        content = line[leading:]

        # Remove space before sentence-ending punctuation
        content = re.sub(r"\s+([.,;:!?])", r"\1", content)
        # Ensure space after punctuation (except at end, before another punct, or file extensions)
        content = re.sub(r"([.,;:!?])(?![a-z]{2,4}\))(?=[^\s\d.,;:!?])", r"\1 ", content)
        # Ensure | has spaces around it (separator)
        content = re.sub(r"\s*\|\s*", " | ", content)
        # Clean up multiple spaces (but not leading)
        content = re.sub(r" +", " ", content)
        # Fix quotes with spaces inside
        content = re.sub(r"'\s+", "'", content)
        content = re.sub(r"\s+'", "'", content)

        cleaned_lines.append(indent + content.strip())
    return "\n".join(cleaned_lines)


def track_element(elem: Element) -> None:
    """Track unhandled tags and classes with example snippets."""
    tag = elem.tag
    if tag not in KNOWN_TAGS and tag not in unhandled_tags:
        # Store first occurrence with XML snippet (truncated to 300 chars)
        snippet = ET.tostring(elem, encoding="unicode")[:300]
        unhandled_tags[tag] = (_current_source_file, snippet)

    for cls in get_class(elem):
        if cls not in HANDLED_CLASSES and not cls.startswith("tg_") and cls not in unhandled_classes:
            snippet = ET.tostring(elem, encoding="unicode")[:300]
            unhandled_classes[cls] = (_current_source_file, snippet)


def format_fraction(elem: Element) -> str:
    """Format a fraction element (class='frac') with nu/dn children."""
    numerator = ""
    denominator = ""

    for child in elem:
        classes = get_class(child)
        if "nu" in classes:
            # Extract only digits from numerator (ignore nested slash element)
            text = "".join(child.itertext())
            numerator = "".join(c for c in text if c.isdigit())
        elif "dn" in classes:
            # Extract only digits from denominator
            text = "".join(child.itertext())
            denominator = "".join(c for c in text if c.isdigit())

    # Try unicode fraction first
    try:
        key = (int(numerator), int(denominator))
        if key in UNICODE_FRACTIONS:
            return UNICODE_FRACTIONS[key]
    except ValueError:
        pass

    # Fallback to superscript/subscript with fraction slash
    sup = "".join(SUPERSCRIPT.get(c, c) for c in numerator)
    sub = "".join(SUBSCRIPT.get(c, c) for c in denominator)
    return f"{sup}⁄{sub}"


def format_inline_content(elem: Element) -> str:
    """
    Format inline content with proper styling (bold, italic, etc).
    Processes element tree recursively.
    """
    result = []

    # Process text before first child
    if elem.text:
        result.append(elem.text)

    # Process children
    for child in elem:
        track_element(child)
        classes = get_class(child)

        # Skip pronunciation markers and structural markers
        if child.tag in (
            "{http://www.apple.com/DTDs/DictionaryService-1.0.rng}prn",
            "{http://www.apple.com/DTDs/DictionaryService-1.0.rng}def",
            "{http://www.apple.com/DTDs/DictionaryService-1.0.rng}pos",
        ):
            if child.tail:
                result.append(child.tail)
            continue

        # Example text - italic
        if "ex" in classes:
            text = normalize_whitespace(format_inline_content(child))
            if text:
                result.append(f"*{text}*")

        # Bold text
        elif "bold" in classes:
            text = normalize_whitespace(format_inline_content(child))
            if text:
                result.append(f"**{text}**")

        # Word form - bold
        elif "f" in classes:
            text = normalize_whitespace(format_inline_content(child))
            if text:
                result.append(f"**{text}**")

        # ge - italic
        elif "ge" in classes:
            text = normalize_whitespace(format_inline_content(child))
            if text:
                result.append(f"*{text}*")

        # sy - italic (grammatical form descriptors like "as adjective")
        elif "sy" in classes:
            text = normalize_whitespace(format_inline_content(child))
            if text:
                result.append(f"*{text}*")

        # tx (taxonomic terms) - bold
        elif "tx" in classes:
            text = normalize_whitespace(format_inline_content(child))
            if text:
                result.append(f"**{text}**")

        # sup (superscript) - convert to superscript
        # Strip surrounding whitespace to keep compact
        elif "sup" in classes:
            if result and result[-1].endswith((" ", "\n", "\t")):
                result[-1] = result[-1].rstrip()
            text = normalize_whitespace(get_all_text(child))
            superscript_text = "".join(SUPERSCRIPT.get(c, c) for c in text)
            result.append(superscript_text)
            if child.tail:
                result.append(child.tail.lstrip())
            continue

        # ty_hom (homograph number) - convert to superscript
        elif "ty_hom" in classes:
            if result and result[-1].endswith((" ", "\n", "\t")):
                result[-1] = result[-1].rstrip()
            text = normalize_whitespace(get_all_text(child))
            superscript_text = "".join(SUPERSCRIPT.get(c, c) for c in text)
            result.append(superscript_text)
            if child.tail:
                result.append(child.tail.lstrip())
            continue

        # subEnt (subscript, e.g., chemical formulas) - convert to subscript
        # Strip surrounding whitespace to keep formulas compact (C₁₁H₁₈ not C ₁₁ H ₁₈)
        elif "subEnt" in classes:
            # Strip trailing whitespace from previous content
            if result and result[-1].endswith((" ", "\n", "\t")):
                result[-1] = result[-1].rstrip()
            text = normalize_whitespace(get_all_text(child))
            subscript_text = "".join(SUBSCRIPT.get(c, c) for c in text)
            result.append(subscript_text)
            # Strip leading whitespace from tail
            if child.tail:
                result.append(child.tail.lstrip())
            continue  # Skip normal tail processing

        # Register label (historical, etc) - italic
        elif "reg" in classes:
            text = normalize_whitespace(format_inline_content(child))
            if text:
                result.append(f"*{text}*")

        # Foreign form in etymology - bold
        elif "ff" in classes:
            text = normalize_whitespace(format_inline_content(child))
            if text:
                result.append(f"**{text}**")

        # Variant word (inside vg) - bold
        elif "v" in classes:
            text = normalize_whitespace(format_inline_content(child))
            if text:
                result.append(f"**{text}**")

        # Label
        elif "lbl" in classes:
            text = normalize_whitespace(format_inline_content(child))
            result.append(text)

        # Grammar group [with object]
        elif "gg" in classes:
            text = normalize_whitespace(get_all_text(child))
            if text:
                result.append(text)

        # Fraction - format as unicode or superscript/subscript
        elif "frac" in classes:
            result.append(format_fraction(child))

        # Numerator/denominator - skip (handled by parent frac)
        elif "nu" in classes or "dn" in classes:
            pass

        # Links - convert to markdown links
        elif child.tag == "a":
            title = child.get("title", "")
            # Extract word text and homograph number separately
            word_text = (child.text or "").strip()
            hom_num = ""
            for link_child in child:
                if has_class(link_child, "ty_hom"):
                    hom_num = get_all_text(link_child).strip()
                else:
                    word_text += get_all_text(link_child)
            word_text = normalize_whitespace(word_text)
            # Format link text with superscript homograph
            if hom_num:
                sup_hom = "".join(SUPERSCRIPT.get(c, c) for c in hom_num)
                link_text = f"{word_text}{sup_hom}"
                filename = f"{title}_{hom_num}.md"
            else:
                link_text = word_text
                filename = f"{title}.md"
            if title and link_text:
                result.append(f"[{link_text}]({filename})")
            elif link_text:
                result.append(link_text)

        # Default: recurse
        else:
            result.append(format_inline_content(child))

        # x_blk: content occupies own line - add newline after element content
        if "x_blk" in classes:
            result.append("\n")

        # Append tail text
        if child.tail:
            result.append(child.tail)

    return "".join(result)


def format_header(root: Element) -> str:
    """Format the entry header: word, homograph, pronunciation, variant."""
    header_parts = []

    # Get word from d:title attribute (cleanest source)
    word = root.get("{http://www.apple.com/DTDs/DictionaryService-1.0.rng}title", "")
    if not word:
        word = root.get("d:title", "")

    # Get homograph number
    hw_elem = find_first_by_class(root, "hw")
    homograph = ""
    if hw_elem is not None:
        hom_elem = find_first_by_class(hw_elem, "ty_hom")
        if hom_elem is not None:
            hom_num = get_all_text(hom_elem).strip()
            homograph = SUPERSCRIPT.get(hom_num, hom_num)

    if word:
        header_parts.append(f"# {word}{homograph}")

    # Find pronunciation
    prx_elem = find_first_by_class(root, "prx")
    if prx_elem is not None:
        pron_text = normalize_whitespace(get_all_text(prx_elem))
        if pron_text:
            header_parts.append(pron_text)

    # Find variant group (e.g., "(also oxford)")
    hg_elem = find_first_by_class(root, "hg")
    if hg_elem is not None:
        vg_elem = find_first_by_class(hg_elem, "vg", direct_only=True)
        if vg_elem is not None:
            vg_text = normalize_whitespace(format_inline_content(vg_elem))
            if vg_text:
                header_parts.append(vg_text)

    return " ".join(header_parts) if header_parts else ""


def format_example_group(elem: Element) -> str:
    """Format example sentences."""
    return normalize_whitespace(format_inline_content(elem))


def format_definition_block(msdict_elem: Element) -> str:
    """Format a single definition block (df + examples)."""
    parts = []

    # Definition text
    df_elem = find_first_by_class(msdict_elem, "df")
    if df_elem is not None:
        df_text = normalize_whitespace(format_inline_content(df_elem))
        parts.append(df_text)

    # Examples
    for eg_elem in find_by_class(msdict_elem, "eg"):
        # Only direct children eg elements
        if eg_elem.getparent() if hasattr(eg_elem, "getparent") else True:
            eg_text = format_example_group(eg_elem)
            if eg_text:
                parts.append(eg_text)

    return " ".join(parts)


def format_sense(se2_elem: Element, is_subsense: bool = False) -> str:
    """Format a numbered sense or bullet subsense."""
    lines = []

    # Get sense number or bullet
    sn_elem = find_first_by_class(se2_elem, "sn", direct_only=True)
    prefix = ""
    if sn_elem is not None:
        sn_text = get_all_text(sn_elem).strip()
        if is_subsense or sn_text == "•":
            prefix = "  - "
        else:
            prefix = f"{sn_text} "

    # Get main definition - only direct msDict children to avoid recursion
    msdicts = find_by_class(se2_elem, "msDict", direct_only=True)
    main_content = []

    for msdict in msdicts:
        classes = get_class(msdict)
        if "t_subsense" in classes:
            # This is a subsense, format separately
            subsense_text = format_subsense(msdict)
            if subsense_text:
                lines.append(subsense_text)
        else:
            # Main sense definition
            # Variant group (e.g., "(also Oxford shoe)") before definition
            vg_elem = find_first_by_class(msdict, "vg", direct_only=True)
            if vg_elem is not None:
                vg_text = normalize_whitespace(format_inline_content(vg_elem))
                if vg_text:
                    main_content.append(vg_text)

            # Label group (e.g., "derogatory") before definition
            lg_elem = find_first_by_class(msdict, "lg", direct_only=True)
            if lg_elem is not None:
                lg_text = normalize_whitespace(format_inline_content(lg_elem))
                if lg_text:
                    main_content.append(lg_text)

            df_elem = find_first_by_class(msdict, "df", direct_only=True)
            if df_elem is not None:
                df_text = normalize_whitespace(format_inline_content(df_elem))
                main_content.append(df_text)

            # Examples in this msDict (direct children only)
            for eg_elem in msdict:
                if has_class(eg_elem, "eg"):
                    eg_text = format_example_group(eg_elem)
                    if eg_text:
                        main_content.append(eg_text)

    if main_content:
        lines.insert(0, prefix + " ".join(main_content))

    return "\n".join(lines)


def format_subsense(msdict_elem: Element) -> str:
    """Format a subsense (bulleted sub-definition)."""
    parts = []

    # Label group (e.g., "historical")
    lg_elem = find_first_by_class(msdict_elem, "lg", direct_only=True)
    if lg_elem is not None:
        lg_text = normalize_whitespace(format_inline_content(lg_elem))
        if lg_text:
            parts.append(lg_text)

    # Definition
    df_elem = find_first_by_class(msdict_elem, "df", direct_only=True)
    if df_elem is not None:
        df_text = normalize_whitespace(format_inline_content(df_elem))
        parts.append(df_text)

    # Examples (direct children only)
    for eg_elem in msdict_elem:
        if has_class(eg_elem, "eg"):
            eg_text = format_example_group(eg_elem)
            if eg_text:
                parts.append(eg_text)

    if parts:
        return "  - " + " ".join(parts)
    return ""


def format_pos_block(se1_elem: Element) -> str:
    """Format a part-of-speech block with all its senses."""
    lines = []
    pos_line_parts = []

    # Part of speech
    pos_elem = find_first_by_class(se1_elem, "pos")
    if pos_elem is not None:
        pos_text = normalize_whitespace(get_all_text(pos_elem))
        if pos_text:
            pos_line_parts.append(f"**{pos_text}**")

    # Grammar info [with object]
    gg_elem = find_first_by_class(se1_elem, "gg")
    if gg_elem is not None:
        gg_text = normalize_whitespace(get_all_text(gg_elem))
        if gg_text:
            pos_line_parts.append(gg_text)

    # Subject label (e.g., "Astronomy", "Chemistry")
    sj_elem = find_first_by_class(se1_elem, "sj")
    if sj_elem is not None:
        sj_text = normalize_whitespace(get_all_text(sj_elem))
        if sj_text:
            pos_line_parts.append(f"*{sj_text}*")

    # Label group in header (e.g., "British English vulgar slang")
    x_xdh_elem = find_first_by_class(se1_elem, "x_xdh", direct_only=True)
    if x_xdh_elem is not None:
        lg_elem = find_first_by_class(x_xdh_elem, "lg", direct_only=True)
        if lg_elem is not None:
            lg_text = normalize_whitespace(format_inline_content(lg_elem))
            if lg_text:
                pos_line_parts.append(lg_text)

    if pos_line_parts:
        lines.append(" ".join(pos_line_parts))
    lines.append("")  # Blank line after POS

    # Check if there are se2 elements (numbered senses)
    has_se2 = False
    for child in se1_elem:
        if has_class(child, "se2"):
            has_se2 = True
            sense_text = format_sense(child)
            if sense_text:
                lines.append(sense_text)

    # If no se2, check for direct msDict definitions under se1
    if not has_se2:
        for child in se1_elem:
            if has_class(child, "msDict"):
                inline_parts: list[str] = []

                # Collect inline content (df, gp, eg) on one line
                for msdict_child in child:
                    classes = get_class(msdict_child)
                    if "note" in classes:
                        # Notes are separate - first flush inline content
                        if inline_parts:
                            lines.append(" ".join(inline_parts))
                            inline_parts = []
                        note_text = format_note(msdict_child)
                        if note_text:
                            lines.append("")
                            lines.append(note_text)
                    elif "df" in classes:
                        df_text = normalize_whitespace(format_inline_content(msdict_child))
                        if df_text:
                            inline_parts.append(df_text)
                    elif "eg" in classes:
                        eg_text = format_example_group(msdict_child)
                        if eg_text:
                            inline_parts.append(eg_text)
                    elif "gp" in classes:
                        # Punctuation like ":" after definition
                        gp_text = get_all_text(msdict_child).strip()
                        if gp_text:
                            inline_parts.append(gp_text)

                # Flush remaining inline content
                if inline_parts:
                    lines.append(" ".join(inline_parts))

    return "\n".join(lines)


def format_subentry_content(subentry: Element) -> list[str]:
    """Format content within a subentry, handling se2 numbered senses and/or direct msDicts.

    Returns a list of formatted lines.
    """
    lines: list[str] = []

    # Check for se2 numbered senses first
    se2_elems = find_by_class(subentry, "se2", direct_only=True)

    if se2_elems:
        # Has numbered senses (1, 2, 3, etc.)
        for se2_elem in se2_elems:
            se2_lines = format_subentry_sense(se2_elem)
            lines.extend(se2_lines)
    else:
        # No numbered senses - process direct msDict elements
        msdicts = find_by_class(subentry, "msDict", direct_only=True)
        for i, msdict in enumerate(msdicts):
            classes = get_class(msdict)
            if "t_subsense" in classes:
                # Subsense
                subsense_text = format_subentry_msdict(msdict, is_subsense=True)
                if subsense_text:
                    lines.append(subsense_text)
            else:
                # Main definition
                main_text = format_subentry_msdict(msdict, is_subsense=False)
                if main_text:
                    lines.append(main_text)

    return lines


def format_subentry_sense(se2_elem: Element) -> list[str]:
    """Format a single se2 numbered sense within a subentry.

    Returns a list of formatted lines.
    """
    lines: list[str] = []

    # Get sense number
    sn_text = ""
    for child in se2_elem:
        if has_class(child, "sn") or has_class(child, "tg_se2"):
            text = get_all_text(child).strip()
            if text and text.isdigit():
                sn_text = text
                break
        # Also check the x_xoh header for sense number
        if has_class(child, "x_xoh"):
            for inner in child:
                if has_class(inner, "tg_se2") or has_class(inner, "sn"):
                    text = get_all_text(inner).strip()
                    if text and text.isdigit():
                        sn_text = text
                        break

    # Get form group (fg) if present at se2 level
    fg_text = ""
    for child in se2_elem:
        if has_class(child, "fg"):
            fg_text = normalize_whitespace(format_inline_content(child))
            break
        # Also check x_xoh header for fg
        if has_class(child, "x_xoh"):
            fg_elem = find_first_by_class(child, "fg")
            if fg_elem is not None:
                fg_text = normalize_whitespace(format_inline_content(fg_elem))
                break

    # Process msDict elements within this sense
    msdicts = find_by_class(se2_elem, "msDict", direct_only=True)
    first_main = True
    for msdict in msdicts:
        classes = get_class(msdict)
        if "t_subsense" in classes:
            # Subsense
            subsense_text = format_subentry_msdict(msdict, is_subsense=True)
            if subsense_text:
                lines.append(subsense_text)
        else:
            # Main definition for this sense
            main_text = format_subentry_msdict(msdict, is_subsense=False)
            if main_text:
                if first_main and sn_text:
                    # Add sense number and optional form group
                    prefix = f"{sn_text} "
                    if fg_text:
                        prefix += f"{fg_text} "
                    lines.append(prefix + main_text)
                    first_main = False
                else:
                    lines.append(main_text)

    return lines


def format_subentry_msdict(msdict_elem: Element, is_subsense: bool = False) -> str:
    """Format a single msDict element from a subentry.

    Args:
        msdict_elem: The msDict element to format
        is_subsense: Whether this is a subsense (bullet point)

    Returns:
        Formatted string for the definition.
    """
    parts: list[str] = []

    # Form group (fg) within this msDict
    fg_elem = find_first_by_class(msdict_elem, "fg", direct_only=True)
    if fg_elem is not None:
        fg_text = normalize_whitespace(format_inline_content(fg_elem))
        if fg_text:
            parts.append(fg_text)

    # Label group (lg)
    lg_elem = find_first_by_class(msdict_elem, "lg", direct_only=True)
    if lg_elem is not None:
        lg_text = normalize_whitespace(format_inline_content(lg_elem))
        if lg_text:
            parts.append(lg_text)

    # Definition
    df_elem = find_first_by_class(msdict_elem, "df", direct_only=True)
    if df_elem is not None:
        df_text = normalize_whitespace(format_inline_content(df_elem))
        if df_text:
            parts.append(df_text)

    # Examples
    for child in msdict_elem:
        if has_class(child, "eg"):
            eg_text = format_example_group(child)
            if eg_text:
                parts.append(eg_text)

    result = " ".join(parts)
    if result and is_subsense:
        return "  - " + result
    return result


def format_phrases_section(block_elem: Element) -> str:
    """Format the PHRASES section."""
    lines = ["---", "", "## PHRASES", ""]

    for subentry in find_by_class(block_elem, "subEntry"):
        # Find header which may contain variant
        x_xoh = find_first_by_class(subentry, "x_xoh")

        # Phrase headword
        l_elem = find_first_by_class(subentry, "l")
        if l_elem is not None:
            phrase = normalize_whitespace(get_all_text(l_elem))
            header_text = f"**{phrase}**"

            # Check for variant group
            if x_xoh is not None:
                vg_elem = find_first_by_class(x_xoh, "vg")
                if vg_elem is not None:
                    vg_text = normalize_whitespace(format_inline_content(vg_elem))
                    if vg_text:
                        header_text += f" {vg_text}"

            lines.append(header_text)

        # Definition content (handles se2 senses and/or direct msDicts)
        content_lines = format_subentry_content(subentry)
        lines.extend(content_lines)

        lines.append("")

    return "\n".join(lines)


def format_phrasal_verbs_section(block_elem: Element) -> str:
    """Format the PHRASAL VERBS section."""
    lines = ["---", "", "## PHRASAL VERBS", ""]

    for subentry in find_by_class(block_elem, "subEntry"):
        # Find header which may contain variant
        x_xoh = find_first_by_class(subentry, "x_xoh")

        # Phrasal verb headword
        l_elem = find_first_by_class(subentry, "l")
        if l_elem is not None:
            phrase = normalize_whitespace(get_all_text(l_elem))
            header_text = f"**{phrase}**"

            # Check for variant group
            if x_xoh is not None:
                vg_elem = find_first_by_class(x_xoh, "vg")
                if vg_elem is not None:
                    vg_text = normalize_whitespace(format_inline_content(vg_elem))
                    if vg_text:
                        header_text += f" {vg_text}"

            lines.append(header_text)

        # Definition content (handles se2 senses and/or direct msDicts)
        content_lines = format_subentry_content(subentry)
        lines.extend(content_lines)

        lines.append("")

    return "\n".join(lines)


def format_derivatives_section(block_elem: Element) -> str:
    """Format the DERIVATIVES section."""
    lines = ["---", "", "## DERIVATIVES", ""]

    for subentry in find_by_class(block_elem, "subEntry"):
        parts = []
        x_xoh = find_first_by_class(subentry, "x_xoh")

        # Derivative word
        l_elem = find_first_by_class(subentry, "l")
        if l_elem is not None:
            word = normalize_whitespace(get_all_text(l_elem))
            parts.append(f"**{word}**")

        # Pronunciation (check both pr and prx)
        pr_elem = find_first_by_class(subentry, "pr")
        if pr_elem is None:
            pr_elem = find_first_by_class(subentry, "prx")
        if pr_elem is not None:
            pron = normalize_whitespace(get_all_text(pr_elem))
            if pron:
                parts.append(pron)

        # Variant group (between pronunciation and POS)
        if x_xoh is not None:
            vg_elem = find_first_by_class(x_xoh, "vg")
            if vg_elem is not None:
                vg_text = normalize_whitespace(format_inline_content(vg_elem))
                if vg_text:
                    parts.append(vg_text)

        # Part of speech
        pos_elem = find_first_by_class(subentry, "pos")
        if pos_elem is not None:
            pos = normalize_whitespace(get_all_text(pos_elem))
            if pos:
                parts.append(pos)

        if parts:
            lines.append(" ".join(parts))
            lines.append("")

    return "\n".join(lines)


def format_origin_section(etym_elem: Element) -> str:
    """Format the ORIGIN/etymology section."""
    lines = ["---", "", "## ORIGIN", ""]

    # Find the content part (x_xo1)
    content_elem = find_first_by_class(etym_elem, "x_xo1")
    if content_elem is not None:
        origin_text = normalize_whitespace(format_inline_content(content_elem))
        lines.append(origin_text)
    else:
        # Fallback: get all text
        origin_text = normalize_whitespace(format_inline_content(etym_elem))
        # Remove the "ORIGIN" label if present
        origin_text = origin_text.replace("ORIGIN", "").strip()
        if origin_text:
            lines.append(origin_text)

    return "\n".join(lines)


def format_note(note_elem: Element) -> str:
    """Format a note element as a markdown blockquote."""
    # Check for label with x_blk (content occupies own line)
    lbl_elem = find_first_by_class(note_elem, "lbl")
    if lbl_elem is not None and has_class(lbl_elem, "x_blk"):
        lbl_text = normalize_whitespace(get_all_text(lbl_elem)).strip()
        # Get raw content with newline preserved
        raw_content = format_inline_content(note_elem)
        if lbl_text:
            # Find the lbl content and the x_blk newline after it
            lbl_idx = raw_content.find(lbl_text)
            if lbl_idx != -1:
                after_lbl = raw_content[lbl_idx + len(lbl_text) :]
                if after_lbl.startswith("\n"):
                    # Found the x_blk newline
                    rest = normalize_whitespace(after_lbl[1:]).strip()
                    lines = [f"> **{lbl_text}**"]
                    if rest:
                        lines.append(f"> {rest}")
                    return "\n".join(lines)

    # Standard handling for notes without x_blk
    parts = []
    if lbl_elem is not None:
        lbl_text = normalize_whitespace(get_all_text(lbl_elem)).strip()
        if lbl_text:
            parts.append(f"**{lbl_text}**")

    # Get the rest of the note content
    content = normalize_whitespace(format_inline_content(note_elem))

    # Remove the label text from content if it was included
    if lbl_elem is not None:
        lbl_text = normalize_whitespace(get_all_text(lbl_elem)).strip()
        if content.startswith(lbl_text):
            content = content[len(lbl_text) :].strip()

    if content:
        parts.append(content)

    if parts:
        return "> " + " ".join(parts)
    return ""


def xml_to_markdown(root: Element) -> str:
    """Convert XML entry to Markdown."""
    sections = []

    # Track root element
    track_element(root)

    def finalize(text: str) -> str:
        """Clean up final text output."""
        return clean_punctuation(text)

    # Header
    header = format_header(root)
    if header:
        sections.append(header)
        sections.append("")

    # Main content (sg block)
    sg_elem = find_first_by_class(root, "sg")
    if sg_elem is not None:
        for child in sg_elem:
            track_element(child)
            if has_class(child, "se1"):
                pos_block = format_pos_block(child)
                if pos_block:
                    sections.append(pos_block)

    # Special sections
    for child in root:
        track_element(child)
        classes = get_class(child)

        if "subEntryBlock" in classes:
            if "t_phrases" in classes:
                sections.append(format_phrases_section(child))
            elif "t_phrasalVerbs" in classes:
                sections.append(format_phrasal_verbs_section(child))
            elif "t_derivatives" in classes:
                sections.append(format_derivatives_section(child))

        elif "note" in classes:
            note_text = format_note(child)
            if note_text:
                sections.append("")
                sections.append(note_text)
                sections.append("")

        elif "etym" in classes:
            sections.append(format_origin_section(child))

    # Clean up punctuation in final output
    result = "\n".join(sections)
    return clean_punctuation(result)


def process_file(xml_path: Path) -> Path:
    """Process a single XML file and create corresponding MD file."""
    global _current_source_file
    _current_source_file = xml_path.name

    content = xml_path.read_text(encoding="utf-8")
    root = ET.fromstring(content)

    markdown = xml_to_markdown(root)

    md_path = xml_path.with_suffix(".md")
    md_path.write_text(markdown, encoding="utf-8")

    return md_path


def process_directory(dir_path: Path) -> int:
    """Process all XML files in directory. Returns count of files processed."""
    xml_files = sorted(dir_path.glob("*.xml"))
    count = 0

    for xml_path in xml_files:
        try:
            md_path = process_file(xml_path)
            print(f"Created: {md_path.name}")
            count += 1
        except ET.ParseError as e:
            print(f"Error parsing {xml_path.name}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing {xml_path.name}: {e}", file=sys.stderr)

    return count


def report_unhandled() -> str:
    """Generate brief summary of unhandled patterns."""
    report = []
    if unhandled_tags:
        report.append(f"Unhandled tags ({len(unhandled_tags)}): {sorted(unhandled_tags.keys())}")
    if unhandled_classes:
        report.append(f"Unhandled classes ({len(unhandled_classes)}): {sorted(unhandled_classes.keys())}")
    return "\n".join(report) if report else "All patterns handled."


def save_unhandled_report(output_path: Path) -> None:
    """Save detailed unhandled patterns report to file with examples."""
    lines = ["# Unhandled Patterns Report", ""]

    if not unhandled_tags and not unhandled_classes:
        lines.append("All patterns handled - no unhandled tags or classes found.")
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return

    if unhandled_tags:
        lines.append("## Unhandled Tags")
        lines.append("")
        for tag in sorted(unhandled_tags.keys()):
            filename, snippet = unhandled_tags[tag]
            lines.append(f"### `{tag}`")
            lines.append(f"**Source:** `{filename}`")
            lines.append("")
            lines.append("```xml")
            lines.append(snippet)
            lines.append("```")
            lines.append("")

    if unhandled_classes:
        lines.append("## Unhandled Classes")
        lines.append("")
        for cls in sorted(unhandled_classes.keys()):
            filename, snippet = unhandled_classes[cls]
            lines.append(f"### `{cls}`")
            lines.append(f"**Source:** `{filename}`")
            lines.append("")
            lines.append("```xml")
            lines.append(snippet)
            lines.append("```")
            lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    """Main entry point."""
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <directory>", file=sys.stderr)
        return 1

    dir_path = Path(sys.argv[1])

    if not dir_path.is_dir():
        print(f"Error: Not a directory: {dir_path}", file=sys.stderr)
        return 1

    print(f"Processing XML files in {dir_path}...")
    count = process_directory(dir_path)
    print(f"Done. Processed {count} files.")

    # Save detailed report to file
    report_path = dir_path / "unhandled_report.md"
    save_unhandled_report(report_path)
    print(f"Unhandled patterns report saved to: {report_path}")

    # Print brief summary
    print()
    print("--- Unhandled Pattern Summary ---")
    print(report_unhandled())

    return 0


if __name__ == "__main__":
    sys.exit(main())
