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


## TODO: remove multiple spaces and asterisks

class TextList(list):
    def append(self, item, value, new_element):
        item = str(item)
        if (not item.strip()):
            return
        item = item.replace('\n', '')       # This cannot be None
        # This can be None
        value = value.strip() if value != None else value
        if len(self) > 0:
            if new_element:
                # Add a new entry for the given pair (item: : value)
                super(TextList, self).append({item: value})
            else:
                old_key = list(self[len(self)-1].keys())[0]
                # Merge the old text with the value of 'item'
                self[len(self)-1] = {old_key + item: value}
        else:
            # The list consist only of the given (item : value)
            super(TextList, self).append({item.strip(): value})


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


def main():
    _dir = "/home/leo/Downloads/"
    #_file = "enwiki-20190101-pages-articles-multistream.xml.bz2"
    _file = "enwiki-20190920-pages-articles-multistream1.xml-p10p30302.bz2"
    dir_name = "data/"
    path = _dir + _file

    try:
        os.makedirs(dir_name, 0o755)
        os.chdir(_dir + dir_name)
    except OSError as e:
        # Don't throw error if the directory already exists
        pass
    except Exception:
        exit(1)

    # Content handler for Wiki XML
    handler = WikiXmlHandler()

    # Parsing object
    parser = xml.sax.make_parser()
    parser.setContentHandler(handler)

    last = 0

    # Iterate through compressed file one line at a time
    for line in subprocess.Popen(['bzcat'], stdin=open(path), stdout=subprocess.PIPE).stdout:
        parser.feed(line)

        if len(handler._pages) % 100 == 0 and len(handler._pages) > last:
            # print(len(handler._pages))
            last = len(handler._pages)

        if (len(handler._pages) == 1 * 1000 * 1000):
            break

    print(len(handler._pages))

    for i in range(len(handler._pages)):
        parse_page(handler, i, dir_name)

    # for t in wiki.filter_templates():
     #   print(t)
    # print(wiki)

    return

    # 17
    for i in range(0, 70):
        page_title, body = handler._pages[67]
        body = strip_text(body)
        #body = beautify_content(body)
        print("({},{})".format(page_title, body))
        return

    return

def parse_page(handler, page_index, path):
    # Create the wiki article
    wiki = mwparserfromhell.parse(handler._pages[page_index])
    text_content = TextList()
    new_element = True
    tag_detected = False
    parenthesis_detected = False

    for n in wiki.nodes[1:]:
        # Avoid parsing the title
        is_tag = False

        if type(n) == mwparserfromhell.nodes.Template or type(n) == mwparserfromhell.nodes.ExternalLink:
            continue
        elif type(n) == mwparserfromhell.nodes.Text:
            buf, tag_detected, parenthesis_detected = get_text(n, tag_detected, parenthesis_detected)
            assert buf != None
            text_content.append(buf, None, new_element)
            new_element = False
            #print(str(type(n)) + "      " + str(buf))

        elif type(n) == mwparserfromhell.nodes.Tag:
            if len(n.contents) > 1:
                buf, tag_detected, parenthesis_detected = get_text(n.contents, tag_detected, parenthesis_detected)
                assert buf != None
                _tmp = buf.strip()
                is_tag = len(_tmp) > 2 and _tmp[0] == "[" and _tmp[-1] == "]"
                if (not is_tag):
                    text_content.append(buf, None, new_element)
                    new_element = False
                    #print(str(type(n)) + "      " + str(n.contents))
                    #print( + "      " + str(n) + "    " + str(n.contents[1]) + "       " + str(type(n.contents)))
                else:
                    n = _tmp

        if type(n) == mwparserfromhell.nodes.Wikilink or is_tag:
            keywords = ["File:", "Category:"]
            skip = False
            for keyword in keywords:
                if n[2:len(keyword)+2] == keyword:
                    skip = True
            if skip:
                continue
            else:
                n = str(n)
                if "|" in n:
                    ls = n.split("|")
                    if len(ls) != 2:
                        continue
                    url, text = ls
                    url = url[2:].lower()
                    text = text[:-2]
                else:
                    url, text = n[2:-2].lower().strip(), n[2:-2]
                new_element = True
                assert text != None
                text_content.append(text, url, new_element)
                #print(str(type(n)) + "      " + str(n))

        else:
            pass
            #print(str(type(n)) + "      " + str(n))

    #print(text_content)

    if len(text_content) == 0 or "REDIRECT" in text_content[0]:
        return
    

    with open('{}/data_{}.json'.format(path, page_index), 'w', encoding='utf-8') as f:
        # Write the parsed wikipedia text to a json file
        json.dump(text_content, f, ensure_ascii=False, indent=4)


def get_text(n, tag_detected, parenthesis_detected):

    buf = ""

    if "|" in n:
        return buf, tag_detected, parenthesis_detected

    for keyword in ["File:", "Category:"]:
        if keyword in n:
            return buf, tag_detected, parenthesis_detected

    while "==" in n:
        if "===" in n:
            #print([x for x in n.split("===") if x.strip()])
            n = " ".join(n.split("===")[0::2])
        elif "==" in n:
            #print([x for x in n.split("==") if x.strip()])
            n = " ".join(n.split("==")[0::2])

    for i in range(len(n)):

        if n[i] == ")":
            parenthesis_detected = False
        elif n[i] == ">":
            tag_detected = False

        elif n[i] == "(":
            parenthesis_detected = True
        elif n[i] == "<":
            tag_detected = True

        elif not tag_detected and not parenthesis_detected and n[i] != "*":
            buf += n[i]
    return buf, tag_detected, parenthesis_detected


def beautify_content(text):
    result = ""
    special_characters = [",", ":", ";", "."]
    return [x for x in text.splitlines() if x.strip()]
    i = 0
    text = [line for line in text.splitlines()]
    while i < len(text):
        if text[i] not in special_characters:
            result += text[i]
            i += 1
        else:
            skip_chars = " \n\t{}".format(text[i])
            while i < len(text) and text[i] in skip_chars:
                i += 1
            if i < len(text):
                result += text[i]
                i += 1
    return result


def strip_text(text):
    result = ""
    strip = 0
    i = 0
    start_angular_index = -1
    end_angular_found = False
    buffer = ""
    keywords_link = ["File:", "Category:"]
    skip_links = 0
    while i < len(text):
        if text[i] == "'" and i+1 < len(text) and text[i+1] == text[i]:
            # Check whether there are 2 or 3 APOSTROPHE charachers and skip them
            is_long_apostrophe = i+2 < len(text) and text[i+2] == text[i+1]
            i = i+3 if is_long_apostrophe else i+2
        elif text[i] == '"':
            i += 1
        elif text[i] == "=" and i + 1 < len(text) and text[i+1] == text[i]:
            # Check whether there are 2 or 3 EQUALS charachers, hence whether it's a normal or big title
            is_main_title = i + \
                2 < len(text) and text[i+2] == "=" and (i +
                                                        3 < len(text) or text[i+3] != "=")
            # Skip to the next possible character using the flag
            j = i+3 if is_main_title else i+2
            # The current value of k is adjusted using a delta which is j-i-1 which will be 1 in case of is_main_title false, and 2 otherwise
            k = len(text) - (j-i-1)
            while (j < k):
                if text[j] == "=" and text[j+1] == text[j] and (not is_main_title or text[j+2] == text[j+1]):
                    if j + 2 < len(text) and (not is_main_title or j + 3 < len(text)):
                        i = j+3 if is_main_title else j+2
                        #print(str(is_main_title) + "" + str(j-i))
                        break
                    else:
                        return result
                j += 1

        char = text[i]

        if char == "[" and i+1 < len(text) and text[i+1] == char:
            if skip_links:
                skip_links += 1
                i += 1
            else:
                for keyword in keywords_link:
                    if keyword == text[i+2:i+2+len(keyword)] or ":" + keyword == text[i+2:i+3+len(keyword)]:
                        skip_links += 1
                        i += 1
                        break

        elif char == "]" and i+1 < len(text) and text[i+1] == char:
            if skip_links:
                skip_links += -1
                i += 1

        elif char == "<":
            if start_angular_index == -1:
                start_angular_index = i
        elif char == "/" and start_angular_index != -1:
            end_angular_found = True
        elif char == ">" and end_angular_found:
            _substr = text[start_angular_index:i]
            result = result.replace(_substr, '')
            buffer = ""
            start_angular_index = -1
            end_angular_found = False

        elif char == "{" or char == "(" or (char == "[" and (i-1 > 0 or i+1 < len(text)) and ((not i-1 > 0 or text[i-1] != char) and (not i+1 < len(text) or text[i+1] != char))):
            # From here the text will be removed since we don't want anything inside it
            strip += 1
        elif char == "}" or char == ")" or (char == "]" and (i-1 > 0 or i+1 < len(text)) and ((not i-1 > 0 or text[i-1] != char) and (not i+1 < len(text) or text[i+1] != char))):
            # Remove text inside the last parenthesis found
            strip += -1
        elif char == "*" or len(result) > 0 and char in " \n" and char == result[-1]:
            # Avoid asterisks or multiple spaces
            pass
        elif not strip and not skip_links:

            if start_angular_index != -1:
                # Add chars to 'buffer' buffer
                buffer += char
            else:
                # Add chars to 'result' buffer
                if len(buffer) > 0:
                    result += buffer
                    buffer = ""
                result += char
        i += 1

    return result


if __name__ == "__main__":
    main()
