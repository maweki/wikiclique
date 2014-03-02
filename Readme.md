# Wikiclique

This script is for finding cliques in the pages of a wikimedia installation.

## Data
You must use gzipped or bz2ipped xml-dumps from a wikimedia installation.

## Temporary File
The temporary file grows to about 110% of the original compressed file. Make
sure you have enough space for that. It is also recommended to not have the
temporary file on the same physical drive as the data file.

## Usage
    wikiclique.py [-h] [--amnt AMNT] [--tmp TMP] [--info INFO] xmlfile

    Finding maximal cliques in Mediawiki's XML-dumps

    positional arguments:
      xmlfile      gz or bz2 xml file as you download it

    optional arguments:
      -h, --help   show this help message and exit
      --amnt AMNT  Number of Cliques to find [default: 10]
      --tmp TMP    Temporary sqlite file [default: ./tmp.sqlite]
      --info INFO  Give an update every [default: 5000]

## Example sources
http://dumps.wikimedia.org/backup-index.html - Downlaod the pages-articles.xml.bz2 file
http://en.memory-alpha.org/wiki/Special:Statistics - Download the pages_current.xml.gz file
Somewhat like that should for every Wikimedia installation.

