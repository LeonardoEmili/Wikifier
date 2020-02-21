import os
import sys
import re
import json
import random
import xml.sax
import subprocess
import bz2
import subprocess
import mwparserfromhell
import wikipedia
import click
import merge_script
from tqdm import tqdm

# A list of subject namespaces following Wikipedia convention's that have to be removed.
EVIL_NAMESPACES = ["File:", "Category:"]
SKIP_NODE = "_skip_node"
TEXT_NODE = "_text_node"
TAG_NODE = "_tag_node"
WIKILINK_NODE = "_wikilink_node"
OTHER_NODE = "_other_node"


class TextList(list):
    def append(self, item, value, new_element):
        item = str(item)
        if (not item):
            return
        # Remove hidden and newline characters from the string
        re_hidden_char = re.compile(r'& *nbsp;|& *ndash;|\\[^ ]*|\n| +')
        item = re.sub(re_hidden_char, ' ', item)

        # Change any number to a constant value
        # CHECK: The 1903 World Series -> The 42 World Series
        # re_numbers = re.compile(r'[+-]*[0-9]+[,.]?[0-9]*')
        # item = re.sub(re_numbers, '42', item)

        # The flag below checks wheter to insert the current element as a separated element.
        new_element = value is not None or (
            list(self[-1].values())[0] is not None) if len(self) > 0 else value is not None

        value = value.strip().title() if value is not None else value
        if len(self) > 0:
            # Override the last element if it's empty
            if new_element and list(self[-1].keys())[0].strip():
                # Add a new entry for the given pair (item: : value)
                super(TextList, self).append({item: value})
            else:
                old_key = list(self[len(self)-1].keys())[0]
                # Merge the old text with the value of 'item'
                self[len(self)-1] = {old_key + item: value}
        else:
            # The list consist only of the given (item : value)
            super(TextList, self).append({item.lstrip(): value})


''' Author reference: https://towardsdatascience.com/wikipedia-data-science-working-with-the-worlds-largest-encyclopedia-c08efbac5f5c '''


class WikiXmlHandler(xml.sax.handler.ContentHandler):
    """Content handler for Wiki XML data using SAX"""

    def __init__(self):
        xml.sax.handler.ContentHandler.__init__(self)
        self._buffer = None
        self._values = {}
        self._current_tag = None
        self._pages = []

    def characters(self, content):
        """Characters between opening and closing tags"""
        if self._current_tag:
            self._buffer.append(content)

    def startElement(self, name, attrs):
        """Opening tag of element"""
        if name in ('title', 'text', 'timestamp'):
            self._current_tag = name
            self._buffer = []

    def endElement(self, name):
        """Closing tag of element"""
        if name == self._current_tag:
            self._values[name] = ' '.join(self._buffer)

        if name == 'page':
            self._pages.append((self._values['title'], self._values['text']))

# Dumps from: https://dumps.wikimedia.org/enwiki/20191201/

dumps_dir = "/home/leo/Downloads/"

def main():
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    #_file = "enwiki-20190101-pages-articles-multistream.xml.bz2"
    _file = "enwiki-20191201-pages-articles-multistream1.xml-p10p30302.bz2"
    dir_name = "../raw_data/"
    # file_path = dumps_dir + _file
    node_dict = {mwparserfromhell.nodes.Template: SKIP_NODE, mwparserfromhell.nodes.ExternalLink: SKIP_NODE,
                 mwparserfromhell.nodes.Text: TEXT_NODE, mwparserfromhell.nodes.Tag: TAG_NODE, mwparserfromhell.nodes.Wikilink: WIKILINK_NODE}
    files = [x for x in os.listdir(dumps_dir) if x.startswith("enwiki")]

    print("Reading Wikipedia dump files located in {}:\n".format(dumps_dir))

    createdumps_dir(dumps_dir, dir_name)

    if (len(files) == 0):
        print("Please provide an input file an try again", file=sys.stderr)

    for filename in files:
        parse_wikidump(filename, dir_name, node_dict)

    generate_occurence_map()
    merge_script.generate_input_data()

    return


def generate_occurence_map():
    occurence_map = dict()
    pages = [p for p in os.listdir("../raw_data/") if p.endswith(".json")]
    for page in pages:
        with open("../raw_data/{}".format(page)) as current_page:
            dict_list = json.load(current_page)
            links = [list(x.values())[0] for x in dict_list if list(x.values())[0] is not None]
            for link in links:
                if link in occurence_map:
                    occurence_map[link] += 1
                else:
                    occurence_map[link] = 1

    with open("occurrences.json", 'w', encoding='utf-8') as f:
        # Write the parsed wikipedia text to a json file without ensuring ascii codification.
        json.dump(occurence_map, f, ensure_ascii=False, indent=4)


def parse_wikidump(filename, dir_name, node_dict):
    # Content handler for Wiki XML.
    handler = WikiXmlHandler()

    # Parsing object.
    parser = xml.sax.make_parser()
    parser.setContentHandler(handler)

    # Avoid spamming prints in the stdout.
    last_num = 0

    # Maximum number of pages to be parsed from each file.
    #PAGES_LIMIT = 1 * 1000 * 1000

    # Iterate through compressed file one line at the time
    for line in subprocess.Popen(['bzcat'], stdin=open(dumps_dir + filename), stdout=subprocess.PIPE).stdout:

        # Feed the parser with a new line.
        parser.feed(line)

        if not len(handler._pages) % 100 and len(handler._pages) > last_num:
            last_num = len(handler._pages)

        # if (len(handler._pages) == PAGES_LIMIT):
        #    break

    print(" \u2022 [{} pages] {}\n".format(len(handler._pages), filename))

    for i in tqdm(range(len(handler._pages))):
        parse_page(handler, i, dir_name, node_dict)
    print()


def createdumps_dir(dumps_dir, dir_name):
    os.makedirs(dir_name, 0o0755, exist_ok=True)

def has_reached_end_of_page(line):
    return "==" in line and "See also" in line or "References" in line or "Footnotes" in line


def parse_page(handler, page_index, path, node_dict):
    # Create the wiki article choosing the curent page from [page index].
    wiki = mwparserfromhell.parse(handler._pages[page_index])

    # A special list created to avoid some complexity in the code.
    text_content = TextList()

    # A bunch of flags, each one is responsible for some parameters.

    # This flag is used togheter with the TextList class to hide some complexity.
    new_element = True

    # These two flags are essentially the same, but maintained separated for allowing nested tags to be removed.
    tag_detected = 0
    parentheses_detected = 0

    # Avoid parsing title line as a line of content
    _, tag_detected, parentheses_detected = clear_text(
        wiki.nodes[0], tag_detected, parentheses_detected)
    wiki.nodes = wiki.nodes[1:]

    page_title = handler._pages[page_index][0]
    if "/" in page_title or "(disambiguation)" in page_title or page_title.startswith("Wikipedia:"):
        return

    for x in wiki.filter_templates():
        if "|" in x:
            hidden_link = x.split("|")[0]
            if "disambiguation" in hidden_link:
                return
        elif "disambiguation" in x:
            return

    # This will read at maximum the first 40 lines of each page to check if it is about a redirect page.
    short_summary = "".join(
        map(lambda x: str(x), wiki.nodes[:min(40, len(wiki.nodes))])).lower()
    if "#redirect" in short_summary or "disambiguation" in short_summary or "/ref" in short_summary or "may refer to:" in short_summary:
        return

    if page_title == "Spring":
        print(wiki.nodes)

    for line in wiki.nodes:

        if has_reached_end_of_page(line):
            break

        line_type = node_dict.get(type(line), OTHER_NODE)
        line, tag_detected, parentheses_detected = clear_text(
            line, tag_detected, parentheses_detected)

        text_content = parse_line(
            line, text_content, new_element, tag_detected, parentheses_detected, line_type)

    # Don't try to write text_content to a file either if it's empty or if it a page of redirect.
    if not text_content or not next(iter(text_content[0].keys())).strip():
        return

    with open('{}{}.json'.format(path, page_title.title()), 'w', encoding='utf-8') as f:
        # Write the parsed wikipedia text to a json file without ensuring ascii codification.
        json.dump(text_content, f, ensure_ascii=False, indent=4)


def parse_line(line, text_content, new_element, tag_detected, parentheses_detected, node_type):
    is_tag = False

    if node_type == SKIP_NODE:
        # Skip lines of templates/external links since we don't need these ones.
        return text_content

    elif node_type == TEXT_NODE:
        # Get the 'buffered' version of the current line and update flags.
        buffer, tag_detected, parentheses_detected = get_text_from(
            line, tag_detected, parentheses_detected)
        previous_was_link = len(text_content) > 0 and list(
            text_content[-1].values())[0] != None
        if previous_was_link:
            leading_sentence = buffer.lstrip()
            is_a_plural_form = len(leading_sentence) > 0 and leading_sentence[0] in "se" and (len(
                leading_sentence) == 1 or (not len(leading_sentence) >= 2 or leading_sentence[1] == ' '))
            if is_a_plural_form:
                link_key, link_value = list(text_content[-1].items())[0]
                del text_content[-1][link_key]
                suffix_char = leading_sentence[0]
                text_content[-1][link_key.strip() + suffix_char] = link_value
                buffer = leading_sentence[2:] if len(
                    leading_sentence) >= 3 else ' '

        # Create a new item in the list representing a node of plain text.
        text_content.append(buffer, None, new_element)
        # Allow text concatenations for future Text nodes.
        new_element = False

    # Current line is of a Tag node and its contents list is not empty.
    elif node_type == TAG_NODE and line:
        # Get the 'buffered' version of the current line and update flags.
        buffer, tag_detected, parentheses_detected = get_text_from(
            line, tag_detected, parentheses_detected)
        # Check if the current line consists of a tag (they're alone in a line if present).
        _tmp = buffer.strip()
        is_tag = len(_tmp) > 2 and _tmp[0] == "[" and _tmp[-1] == "]"

        if (not is_tag):
            # Create a new item in the list representing a node of plain text.
            text_content.append(buffer, None, new_element)
            # Allow text concatenations for future Text nodes.
            new_element = False

    # This is the case where either the current line is a Wikilink node or it has been recognised to be a tag.
    if node_type == WIKILINK_NODE or is_tag:

        # Check if the current link is a piped link: https://en.wikipedia.org/wiki/Wikipedia:Piped_link
        is_piped_link = "|" in line

        for keyword in EVIL_NAMESPACES:
            if line[2:len(keyword)+2] == keyword:
                # Skip the current line if it consists of one of the namespaces to be avoided.
                return text_content
        else:
            line = str(line)
            if is_piped_link:
                # If it is a piped link that split it into two or more halves.
                links = line.split("|")

                if len(links) != 2:
                    # It's not supported if there are more than one pipe characters in the current line.
                    return text_content

                # Take both the url and its textual representation inside the wikipedia page and clean them from double square brackets.
                url, text = links
                # Since this will the key for each page it's only used as lowercased.
                url = url[2:].lower()
                text = text[:-2]
            else:
                # They're essentially the same thing, but as usually the key is first lowered or unique purposes.
                # maybe replace lower() with title()
                url, text = line[2:-2].lower().strip(), line[2:-2]
            url = url.lower().strip()
            new_element = True
            text_content.append(text, url, new_element)

    return text_content


def clear_text(line, tag_detected, parentheses_detected):

    # This buffer will hold the parsed line string after the process.
    result_buffer = ""

    # A list of characters to be avoided when returning the current line.
    EVIL_CHARACTERS = ["*", "'", '"', "`", "#", "="]

    # Clean the current line from unwanted headers. (i.e. main titles in a wikipedia page).
    line = remove_headers(line)

    if line.lstrip() and line.strip()[0] == "*":
        return " ", tag_detected, parentheses_detected

    for char in line:

        # Parentheses check from here.
        if char in ")}":
            parentheses_detected += -1
        elif char == ">":
            tag_detected += -1
        elif char in "({":
            parentheses_detected += 1
        elif char == "<":
            tag_detected += 1
        # Parentheses check up to here.

        # Add [char] to the current line only if it is not in the range of such a parentheses or it is an unwanted character.
        elif not tag_detected and not parentheses_detected and char not in EVIL_CHARACTERS:
            result_buffer += char

    return result_buffer, tag_detected, parentheses_detected


def get_text_from(line, tag_detected, parentheses_detected):

    # Remove external links from text content
    line = re.sub(r'\[[^]]*\][^]]', ' ', line)

    # Remove links within a text node, this is a loss of links and should be improved in the future
    # HINT: mwparser doesn't recognize them as Wikilinks, should use recursion
    line = " ".join([x.split("|")[1][:-2] if i % 2 and "|" in x else x.replace(
        "[", "").replace("]", "") for i, x in enumerate(re.split(r"(\[[^]]*\]\])", line))])

    # Remove these kind of dirty lines, they will not be useful in terms of training set.
    if line.lstrip() and "|" == line.lstrip()[0]:
        return " ", tag_detected, parentheses_detected

    # Skip the current line if it consists of one of the namespaces to be avoided.
    for keyword in EVIL_NAMESPACES:
        if keyword in line:
            return " ", tag_detected, parentheses_detected

    # This buffer will hold the parsed line string after the process.
    result_buffer = ""

    # A list of characters to be avoided when returning the current line.
    EVIL_CHARACTERS = ["*", "'", '"', "#", "="]

    for char in line:

        if char == "[":
            parentheses_detected += 1
        elif char == "]":
            parentheses_detected += -1
        elif not tag_detected and not parentheses_detected and char not in EVIL_CHARACTERS:
            result_buffer += char

    return line, tag_detected, parentheses_detected


''' This function is responsible for removing headers from the current line'''


def remove_headers(line):
    while "==" in line:
        if "===" in line:
            line = " ".join(line.split("===")[0::2])
        elif "==" in line:
            line = " ".join(line.split("==")[0::2])
    return line


if __name__ == "__main__":
    main()
