"""
mac_dict_to_md - Convert macOS Dictionary XML to Markdown.

This package provides tools for:
- Splitting large dictionary XML files into individual entries (split)
- Parsing dictionary XML entries into Markdown format (parse)
- Converting XML elements to Markdown (convert)
"""

from mac_dict_to_md.parse import (
    xml_to_markdown,
    process_file,
    process_directory,
    format_header,
    format_inline_content,
    format_pos_block,
    format_sense,
    format_subsense,
    format_phrases_section,
    format_derivatives_section,
    format_origin_section,
    format_note,
    format_fraction,
    get_class,
    has_class,
    find_by_class,
    find_first_by_class,
    get_direct_text,
    get_all_text,
    normalize_whitespace,
    clean_punctuation,
    track_element,
    report_unhandled,
    save_unhandled_report,
)

from mac_dict_to_md.split import (
    Entry,
    make_filename,
    extract_title,
    extract_homograph,
    find_entries,
    save_entry,
    process_entries,
    split_dictionary,
)

from mac_dict_to_md.convert import (
    load_and_process_xml,
    find_matching_item,
    convert_to_markdown,
    save_entry_to_md,
)

__version__ = "0.1.0"
