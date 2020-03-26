# Wikifier

Wikification is the process of labeling input sentences into concepts from Wikipedia. The repository contains a major script for scraping text from Wikipedia dumps and parsing it into a dataset, the model for annotating sentences and an asynchronous web scraper for generating the dataset dynamically starting from a Wikipedia page used as seed.

### Prerequisites

You can install the required dependencies using the Python package manager (pip):

```
pip3 install aiohttp
pip3 install cchardet
pip3 install aiodns
pip3 install wikipedia
pip3 install requests
```

## Getting Started

First, we need to get the data. Wikiparser is a web scraper that loads dumps from XML files and stores the dataset as a collection of compressed files. You can run the script using the following syntax:

```
python3 WikiParser.py [OPTION]... URL... [-n NUM]
python3 WikiParser.py [OPTION]... [-n NUM]
python3 WikiParser.py [OPTION]... URL...
```

## Built With

* [AIOHTTP](https://docs.aiohttp.org/en/stable/index.html) - Asynchronous HTTP Client used
* [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) - Library for parsing HTML
* [mwparserfromhell](https://github.com/earwig/mwparserfromhell) - A parser for MediaWiki wikicode
* [wikipedia](https://pypi.org/project/wikipedia/) - A wrapper for the MediaWiki API

## Authors

* **Leonardo Emili** - [LeonardoEmili](https://github.com/LeonardoEmili)

