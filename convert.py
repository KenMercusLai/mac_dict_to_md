from typing import List
import xml
import re
import xml.etree.ElementTree as ET


def load_and_process_xml(file_path: str) -> list[str | None]:
    # Opening and parsing the XML file
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Define the namespace map
        namespaces = {"d": "http://www.apple.com/DTDs/DictionaryService-1.0.rng"}

        # Extract elements within the <d:dictionary> tag using the appropriate namespace
        dictionary_entries = []

        # Processing all <d:entry> elements to ensure they have a non-empty d:title attribute
        for entry in root.findall(".//d:entry", namespaces=namespaces):
            title = entry.get(
                "{http://www.apple.com/DTDs/DictionaryService-1.0.rng}title"
            )
            # Check if title exists and is not just whitespace
            if title is not None and title.strip():
                entry_string = ET.tostring(entry, encoding="unicode")
                dictionary_entries.append(entry_string)

        # Return list of entry strings
        return dictionary_entries

    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def find_matching_item(
    items: List, pattern: str
) -> tuple[str, re.Match] | tuple[None, None]:
    """Search for an item in the list that matches the given regex pattern and return it."""
    for item in items:
        if matched := re.match(pattern, item):
            return item, matched
    return tuple([None, None])


def convert_to_markdown(elem, depth=0):
    # This function recursively converts XML content to Markdown
    markdown = ""

    # Process child elements first (depth-first)
    for child in elem:
        markdown += convert_to_markdown(child, depth + 1)

    # Process the current element
    # Check for class attributes/classes or specific tags
    tag = elem.tag
    class_attr = elem.get("class", "").split(" ")
    text = elem.text if elem.text is not None else ""
    tail_text = elem.tail if elem.tail is not None and depth > 0 else ""
    print(tag, class_attr, text, tail_text)

    # markdown is the content of child elements
    # text is the content of the current element
    # in each element, content is organized, allegedly, text + markdown(from children) + tail_text

    # italic
    if "ex" in class_attr or "ge" in class_attr or "reg" in class_attr:
        markdown = f"*{(text + markdown + tail_text).strip()}* "
    # internal link
    elif tag == "{http://www.w3.org/1999/xhtml}a":
        markdown = f"[[{(text + markdown + tail_text).strip()}]]"
    # bold
    elif "l" in class_attr:
        markdown = f"**{(text + markdown + tail_text).strip()}** "
    # section
    else:
        markdown = text + markdown + tail_text

    # Pattern to match
    pattern = r"^x_x([a-zA-Z][a-zA-Z\d]*?)(\d*)$"
    # Find matching item
    matched_item, matched_section = find_matching_item(class_attr, pattern)

    if matched_item:
        (matched_section_type, matched_section_indent) = matched_section.groups()
        print(
            f"Matching item: {matched_item}, matched: {matched_section_type, matched_section_indent}"
        )
        if matched_section_indent is not None and "sn" not in class_attr:
            # not serial number (bullet)
            markdown = markdown + "\n\n"
    else:
        print("No matching item found.")

    return markdown


def save_entry_to_md(entry_xml: str):
    try:
        # Parse the entry XML string
        entry: xml.etree.ElementTree = ET.fromstring(entry_xml)

        # Define the namespace map
        namespaces = {
            "html": "http://www.w3.org/1999/xhtml",
            "ns0": "http://www.apple.com/DTDs/DictionaryService-1.0.rng",
        }

        # Extract the title attribute for use as the filename
        title = entry.get("{http://www.apple.com/DTDs/DictionaryService-1.0.rng}title")

        if title is None or not title.strip():
            print("Entry is missing a valid 'd:title'. Skipping file creation.")
            return

        # Clean title to create a valid filename
        filename = (
            title.strip().replace("/", "_").replace("\\", "_").replace(":", "_") + ".md"
        )

        # Create and write to a Markdown file
        with open(filename, "w", encoding="utf-8") as file:
            file.write(convert_to_markdown(entry))

        print(f"File '{filename}' has been created successfully.")

    except ET.ParseError:
        print("Failed to parse the XML entry. Ensure it's well-formed.")
    except Exception as e:
        print(f"An error occurred: {e}")


# Define the file path
file_path = "Oxford Dictionary of English.xml"

# Process the XML and store results
dictionary_contents = load_and_process_xml(file_path)

# Output the results
print(f"Number of entries: {len(dictionary_contents)}")
for content in dictionary_contents[10000:10020]:
    save_entry_to_md(content)
