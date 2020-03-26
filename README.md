# Wikifier

Wikification is the process of labeling input sentences into concepts from Wikipedia. The repository contains: a major script for scraping text from Wikipedia dumps and parsing it into a dataset, the model for annotating sentences and an asynchronous web scraper for generating the dataset dinamically starting from a Wikipedia page used as seed.

### Prerequisites

The project uses python3 as intepreter but also need some more requirements. The below commands make use of pip3 package installer so in order to use them you need to install it as well.

```
pip3 install aiohttp
pip3 install cchardet
pip3 install aiodns
```

## Getting Started

You need to get data first. In order to do it run WikiParser simply by using one of the following syntaxes:

```
python3 WikiParser.py [OPTION]... URL... [-n NUM]
python3 WikiParser.py [OPTION]... [-n NUM]
python3 WikiParser.py [OPTION]... URL...
```

## Built With

* [AIOHTTP](https://docs.aiohttp.org/en/stable/index.html) - Asynchronous HTTP Client used
* [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) - Library for parsing HTML

## Authors

* **Leonardo Emili** - [LeonardoEmili](https://github.com/LeonardoEmili)

