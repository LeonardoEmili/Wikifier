#!/usr/bin/python
# -*- coding: utf-8 -*-

# For installing pycurl:
#   apt install libcurl4-openssl-dev libssl-dev
#   apt-get install python3-dev
#   pip3 install pycurl               -->     pycurl
#   https://aiohttp.readthedocs.io/en/stable/ ???

# TODO: fix links such as
#   https://en.wiktionary.org/wiki/Reconstruction:Proto-Uralic/k%C3%A4%C4%8Fw%C3%A4

import os, sys, re, json, requests, json, asyncio, random
from urllib.request import urljoin
from bs4 import BeautifulSoup, NavigableString, Tag, Comment
from aiohttp import ClientSession
from optparse import OptionParser

''' A special kind of list used for having a more compact code, essentially it checks if the item
    to be added has to be inserted as a new element or as part of the preceding one. The last one
    is the case of plain text followed by more plain text non-separated by a paragraph. '''
class TextList(list):
    def append(self, item, value, new_element):
        item = item.replace('\n', '')       # This cannot be None
        value = value.replace('\n', '') if value != None else value      # This can be None
        if len(self) > 0:
            if new_element:
                super(TextList, self).append({item : value})        # Add a new entry for the given pair (item: : value)
            else:
                old_key = list(self[len(self)-1].keys())[0]
                self[len(self)-1] = {old_key + item : value}        # Merge the old text with the value of 'item'
        else:
            super(TextList, self).append({item : value})        # The list consist only of the given (item : value)

async def main():
    output_no = 0       # Just a index used to print json structure to file in the form of data_{output_no}.json
    options = get_options(sys.argv)     # Here we parse the options
    seed_url = ["https://en.wikipedia.org/wiki/Cat"]        # This seed url initializes the list of urls used to generate random pages
    generated_urls = set(seed_url)
    visited_urls = set()        # Used to keep track of already visited urls
    for i in range(1, len(sys.argv)):
        if sys.argv[i].startswith("-"): continue        # These are options and then not parsed here
        output_no, new_urls = await scrape_website(sys.argv[i], options, output_no, visited_urls)
        generated_urls = generated_urls | new_urls - visited_urls       # Update the value of generated_urls by adding new_urls but clearing it from already visited_urls
    while options.NUM > 0:      # In the case the user asked for NUM more pages to be parsed they're randomically selected using 'generated_urls' list
        sample_size = min(len(generated_urls), options.NUM)
        options.NUM -= sample_size
        for url in random.sample(generated_urls, sample_size):      # Random sample without replacing
            output_no, new_urls = await scrape_website(url, options, output_no, visited_urls)
            generated_urls = generated_urls | new_urls - visited_urls
    return

''' Here we parse the website related to its url and if asked also link redirects are resolved. '''
async def scrape_website(url, options, output_no, visited_urls):
    wikipedia_url_re = re.compile('^(https?://)?([A-z]{2}\.)?wikipedia\.org')   # Check if the given link is owned by Wikipedia
    print(url)
    if (not wikipedia_url_re.match(url)):
        print('The url {} cannot be processed. Remember that only Wikipedia\'s links are allowed (e.g. https://en.wikipedia.org/wiki/Cat)'.format(url)
            , file=sys.stderr)
        return (output_no, set())
    hashtag_ref_re = re.compile('#.*$')     # Capture using regex url ending with #some_id
    url = re.sub(hashtag_ref_re, '', url)       # Remove the trailing references (useless in this script)
    try:
        data = parse_website(url)               # Main stuff going here, it extracts content text from page
        visited_urls.add(url)
    except Exception as e:
        print("Runtime error: {} cannot be processed due to some errors, it will be ignored.".format(url))
        return (output_no, set())       # Empty set and same output_no are returned in case of error
    if options.check_link_redirects:        # If asked it will resolve url redirects
        data = await resolve_redirects(data)
    with open('data_{}.json'.format(output_no), 'w', encoding = 'utf-8') as f:
        json.dump(data, f, ensure_ascii = False, indent = 4)        # Write the parsed wikipedia text to a json file
    return (output_no + 1,      # Update the value of output_no
            {data_dict[list(data_dict.keys())[0]] for data_dict in data if data_dict[list(data_dict.keys())[0]] != None})   # Return a list of only urls

''' It will create a list of urls each one being a valid url or None in case plain text which hasn't a link url
    and for each given source url tries to get the 'canonical' url that is the redirected url. Note that this
    method does it by downloading each page and causes then a large overhead then a lot of time to parse a page.
    TODO improvements: get the redirected url without loading the entire html page '''
async def resolve_redirects(data):
    urls = [word_dict[list(word_dict.keys())[0]] for word_dict in data]     # Take the value of each pair {key : value} that is None in case of plain text as key
    async with ClientSession(loop = loop) as session:
        result = await fetch_all(session, urls)
        assert len(result) == len(data)         # We want to create a result list which has the same length as data for faster item retriving purposes
        return [{list(data[i].keys())[0] : result[i][list(result[i].keys())[0]]}        # A list of pairs, each one of the form {link_text : resolved_url}
                if data[i][list(data[i].keys())[0]] != None else data[i] for i in range(len(data))]     # or {plain_text : None} in case of None value

''' This method is responsible for calling the fetch method for each of the given urls. '''
async def fetch_all(session, urls):
    return await asyncio.gather(*[fetch(session, url) for url in urls])     # Wait for each url to be fetched

''' It will do a GET request for each source_url and then get the target link by looking at the canonical link in the html
    using a regex. Note that source_url may not be a valid url, in this case it is parsing plain text which we don't want
    to do here hence it will return a placeholder pair {None, None}. '''
async def fetch(session, source_url):
    if source_url == None: return {None, None}     # In this case it would try to parse plain text, then a placeholder is returned
    async with session.get(source_url) as response:
        re_match = re.compile('<link rel="canonical" href="(.*)"/>')    # Capture using regex what's inside 'href' attribute
        link_matched = re_match.search(await response.text())
        return {source_url : link_matched.group(1)} if link_matched != None else {source_url : source_url}

''' Here we parse each of the given url from command line by removing unnecessary tags and processing the remaining
    plain text and text with associated links (hyperlinks). '''
def parse_website(url):
    response = requests.get(url)
    if response.status_code >= 400 and response.status_code <= 500:     # Status code in range 400-500 then some errors occurred
        sys.tracebacklimit = 0      # Avoid printing the whole traceback
        raise Exception()
    soup = BeautifulSoup(response.content, "html.parser").find("div", {"class": "mw-parser-output"})
    # The command above parsers the required url by looking at content starting from this 'div'
    clear_tags(soup)    # Clear soup from undesidered tags
    text_content = TextList()       # This list will store all the pairs as the form: (link_text : link_url) or (text: None)
    for paragraph in soup.find_all("p"):
        new_element = True  # Maintain each paragraph separated and links separated from plain text
        for el in paragraph.contents:
            if (el.name == 'a'):
                new_element = True  # We want the method to add it as a separated entry into the list
                link_url = urljoin(url, el.get('href'))     # Join between base 'url' and 'link_url' which is relative to it
                text_content.append(el.get_text(), link_url, new_element)
            elif isinstance(el.string, Tag) and el.get_text().strip():
                text_content.append(el.get_text(), None, new_element)   # Add entry by checking the value of 'new_element' flag
                new_element = False
            elif isinstance(el.string, NavigableString) and el.strip(): # Add entry by checking the value of 'new_element' flag
                text_content.append(el, None, new_element)
                new_element = False
    return text_content

''' This clears unwanted tags from the html page but is also responsible for replacing "styling" tags
    with their comments, for example <i>Ciao</i> will be translated to Ciao '''
def clear_tags(soup):
    invalid_tags = ["table", "ul", "ol", "dl", "h1", "h2", "h3", "h4", "h5", "em", "code", "q", "var", "abbr",      # A list of invalid tags
                    "sup", "sub", "a", "div", "span", "style", "u", "i", "b", "img", "small", "big", "s"]
    # TODO: maybe the <s> tag has to be removed since it reports that such information is no longer correct
    for u in soup.find_all(invalid_tags):
        if u.name == "a" and (u.get('href') == None or u.get('href')[0] == '#'):
            u.extract()
        elif (u.name == "u" or u.name == "i" or u.name == "b" or u.name == "small" or u.name == "abbr" or u.name == "big" or u.name == "s" or u.name == "q" or u.name == "var"):
            u.replaceWithChildren()
        elif u.name == "img":
            u.decompose()
        elif u.name in invalid_tags and u.name != "a":
            u.extract()
    upper_label = soup.find("div", {"class": "hatnote navigation-not-searchable"})
    if upper_label is not None:
        upper_label.extract()     # Remove the upper label where it says 'page x redirects here ... etc ...'
    short_description = soup.find("div", {"class": "shortdescription nomobile noexcerpt noprint searchaux"})
    if short_description is not None:
        short_description.extract()     # Remove the shortdescription
    for comment in soup.find_all(string = lambda text: isinstance(text, Comment)):
        comment.extract()     # Remove all comments

''' An utility function used to define and parse command line options. '''
def get_options(argv):
    parser = OptionParser(usage = "python3 %prog [OPTION]... URL... [-n NUM]\n   or: %prog [OPTION]... -n NUM\n   or: %prog [OPTION]... URL...\nParse wikipedia pages either from URL from NUM random pages.",
                            description= "URLs or NUM are mandatory in order to use this script, look above for usages.")
    parser.add_option("-l", "--links", dest = "check_link_redirects", action = "store_true",
                        help = "resolve link redirects", default = False)
    parser.add_option("-n", "--number", dest = "NUM", action = "store", type = "int",
                        help = "generate NUM random pages text from wikipedia", default = None)
    options, args = parser.parse_args()
    try:
        # Check if at least one URL is given or if the user submitted a value for NUM
        if len(argv) <= 1 and options.NUM == None or options.NUM <= 0: 
            sys.tracebacklimit = 0      # Avoid printing the whole traceback
            raise SyntaxError()
    except SyntaxError as e:
        exit("{}: missing mandatory arguments\nTry 'python3 {} -h' or 'python3 {} --help' for more information.".format(sys.argv[0], sys.argv[0], sys.argv[0]))
    if options.NUM == None:     options.NUM = 0     # Restore its default value
    return options


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()