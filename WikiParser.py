#!/usr/bin/python3
# -*- coding: utf-8 -*-

# For installing pycurl:
#   apt install libcurl4-openssl-dev libssl-dev
#   apt-get install python3-dev
#   pip3 install pycurl               -->     pycurl
#   

# TODO: fix links such as
#   https://en.wiktionary.org/wiki/Reconstruction:Proto-Uralic/k%C3%A4%C4%8Fw%C3%A4

import os, sys, time, re, xml.etree, json, requests, pycurl, urllib.request, json
from urllib.request import urlopen, urljoin
from bs4 import BeautifulSoup, NavigableString, Tag, Comment
from io import StringIO
from optparse import OptionParser

''' A special kind of list used for having a more compact code, essentially it checks if the item to be added has to be inserted as a new element
    or as part of the preceding one. The last one is the case of plain text followed by more plain text non-separated by a paragraph. '''
class TextList(list):

    def append(self, item, value, new_element, options):
        item = item.replace('\n', '') if (not options.keep_newline and item != None) else item
        value = value.replace('\n', '') if (not options.keep_newline and value != None) else value
        if len(self) > 0:
            if new_element:
                super(TextList, self).append({item : value})
            else:
                old_key = list(self[len(self)-1].keys())[0]
                self[len(self)-1] = {old_key + item : value}
        else:
            super(TextList, self).append({item : value})

class CurlStream(object):

    curl_count = 0
    curl_storage = []

    def __init__(self):
        self.curl_multi = pycurl.CurlMulti()

    def add_request(self, request, post_fields=None):
        self.curl_count += 1
        curl = self._create_curl(request, post_fields)
        self.curl_multi.add_handle(curl)

    def perform(self):
        while self.curl_count:
            while True:
                response, self.curl_count = self.curl_multi.perform()
                if response != pycurl.E_CALL_MULTI_PERFORM:
                    break
            self.curl_multi.select(1.0)

    # Maybe unnecessary
    #def read_all(self):
        #for response in self.curl_storage:
            #print(response) # this does nothing --prints blank lines
            #print()

    def close(self):
        self.curl_multi.close()

    def _create_curl(self, request, post_fields):
        curl = pycurl.Curl()
        curl.setopt(curl.URL, request)
        curl.setopt(curl.WRITEFUNCTION, self.write_out)
        curl.setopt(curl.TIMEOUT, 20)
        # Below is the important bit, I am now adding each curl object to a list
        self.curl_storage.append(curl)
        return curl

    def write_out(self, data):
        #print(BeautifulSoup(data, "html.parser"))
        return len(data)



def main():
    parser = OptionParser()
    parser.add_option("-k", "--keep", dest = "keep_newline", action = "store_true", help = "keep newlines '\n' from text, by default they are cleared from text", default = False)
    (options, args) = parser.parse_args()
    for i in range(1, len(sys.argv)):
        # Arguments starting with -- or - are to be considered options and then not computed here
        if sys.argv[i].startswith("-"): continue
        data = scrape_website(sys.argv[i], options)
        with open('data.json', 'w', encoding = 'utf-8') as f:
            json.dump(data, f, ensure_ascii = False, indent = 4)
    return

    #xd = "https://en.wikipedia.org/wiki/UK"
    #headers = {"Range": "bytes=0-2"}  # first 100 bytes
    #print(requests.get(xd, headers=headers).content)


def scrape_website(url, options):
    # Process the Webpage with BeautifulSoupwith content starting from this 'div'
    soup = BeautifulSoup(urllib.request.urlopen(url), "html.parser").find("div", {"class": "mw-parser-output"})
    # Clear soup from undesidered tags
    clear_tags(soup)

    # The list 'text_content' above will store all the pairs as the form: (link_text : url) or (text: None)
    text_content = TextList()
    
    for paragraph in soup.find_all("p"):
        # We set 'new_element' flag for each paragraph to maintain the document structure, it's purpose is for separating text from links and viceversa
        new_element = True
        for el in paragraph.contents:
            if (el.name == 'a'):
                # Since we have found another link then we force the method to add a separated entry to the list
                new_element = True
                text_content.append(el.get_text(), urljoin(url, el.get('href')), new_element, options)
            elif isinstance(el.string, Tag) and el.get_text().strip():
                text_content.append(el.get_text(), None, new_element, options)
                new_element = False
            elif isinstance(el.string, NavigableString) and el.strip():
                text_content.append(el, None, new_element, options)
                new_element = False
    return text_content


# This clears unwanted tags from the html page but is also responsible for
# replacing "styling" tags with their comments, for example <i>Ciao</i> will be translated to Ciao
def clear_tags(soup):
    # Here it is a list of the tags we want to clear
    invalid_tags = ["table", "ul", "ol", "dl", "div", "a",
                    "sup", "sub", "h1", "h2", "h3", "h4", "h5",
                    "span", "style", "u", "i", "b"]
    for u in soup.find_all(invalid_tags):
        if u.name == "a" and (u.get('href') == None or u.get('href')[0] == '#'):
            u.extract()
        elif (u.name == "u" or u.name == "i" or u.name == "b"):
            u.replaceWithChildren()
        elif u.name in invalid_tags and u.name != "a":
            u.extract()
    # remove some useless tags, here it is the upper label
    a = soup.find("div", {"class": "hatnote navigation-not-searchable"})
    if a is not None:
        a.extract()
    # it is the shortdescription
    a = soup.find("div", {"class": "shortdescription nomobile noexcerpt noprint searchaux"})
    if a is not None:
        a.extract()
    for c in soup.find_all(string=lambda text: isinstance(text, Comment)):
        c.extract()

if __name__ == "__main__":
    main()
