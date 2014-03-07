#!/bin/python3
import xml.etree.ElementTree as ET
import sqlite3
import os
import sys
import functools

args = None
conn = None
result = None

def parse_args():
    import argparse

    parser = argparse.ArgumentParser(description='Finding maximal cliques in Mediawiki\'s XML-dumps')
    parser.add_argument('xmlfile', help='gz or bz2 xml file as you download it', type=argparse.FileType('rb'))
    parser.add_argument('--amnt', type=int, default=10, help='Number of Cliques to find [default: 10]')
    parser.add_argument('--tmp', default='./tmp.sqlite', help='Temporary sqlite file [default: ./tmp.sqlite]')
    parser.add_argument('--info', type=int, default=5000, help='Give an update every [default: 5000]')
    global args
    args = parser.parse_args()

def init_db():
    import os.path
    abspath = os.path.abspath(args.tmp)
    if os.path.isdir(abspath) or os.path.isfile(abspath):
        print('Cannot create temporary database')
        sys.exit(1)
    global conn
    conn = sqlite3.connect(abspath)
    print('Creating temporary Database')
    c = conn.cursor()
    queries = [
        'DROP TABLE IF EXISTS cons',
        'DROP TABLE IF EXISTS pages',
        'CREATE TABLE pages (id INTEGER PRIMARY KEY AUTOINCREMENT, pagename TEXT UNIQUE ON CONFLICT IGNORE)',
        'CREATE TABLE cons (fromid INTEGER REFERENCES pages (id), toid INTEGER REFERENCES pages (id))',
        'CREATE INDEX fromindex ON cons (fromid)',
        'CREATE INDEX toindex ON cons (toid)',
    ]
    for count, q in enumerate(queries):
        c.execute(q)
    conn.commit()
    print('done')
    return conn

def get_xml_parser(xmlfile):
    import gzip
    import bz2
    trying = [bz2.open, gzip.open]
    for method in trying:
        xmlfile.seek(0)
        f = method(xmlfile)
        try:
            f.read(256)
            f.seek(0)
            return ET.iterparse(f)
        except:
            pass

def cleanup():
    conn.close()
    os.unlink(os.path.abspath(args.tmp))

def create_graph(xmlparser, database, origin_stream):
    c = database.cursor()

    @functools.lru_cache(maxsize=8388608, typed=False)
    def addPage(page):
        c.execute('INSERT OR IGNORE INTO pages VALUES(NULL  , ?)', (page,))

    @functools.lru_cache(maxsize=8388608, typed=False)
    def getIdFromPagename(page):
        id_, = next(c.execute('SELECT id FROM pages WHERE pagename = ? LIMIT 1', (page,)))
        return id_

    def addToDatabase(article, children):
        addPage(article)
        fromid = getIdFromPagename(article)
        for ch in children:
            addPage(ch)
            toid = getIdFromPagename(ch)
            c.execute('INSERT INTO cons VALUES (?, ?)', (fromid, toid))

    article_count = 0
    next_info = args.info
    first = None

    origin_size = os.stat(origin_stream.fileno()).st_size

    import re

    for event, elem in xmlparser:
        if elem.tag.endswith('page'):
            namespace = elem.tag[1:-len('page')-1]
            article = elem.find('{'+namespace+'}'+'title').text
            revision = elem.find('{'+namespace+'}'+'revision')
            content = revision.find('{'+namespace+'}'+'text').text

            article_count += 1
            if article_count >= next_info:
                progress = (origin_stream.tell() / origin_size)*100
                print('Analyzing article', round(progress,2),'%', article_count, article)
                next_info += args.info

            children = set()
            try:
                for result in re.findall('\[\[.*?\]\]', content):
                    actual = result.strip('[]')
                    if '|' in actual:
                        actual = actual.partition('|')[0]
                    if '#' in actual:
                        actual = actual.partition('#')[0]
                    children.add(actual)
            except:
                pass
            addToDatabase(article, children)
            elem.clear()
    database.commit()
    print('done')
    getIdFromPagename.cache_clear()
    addPage.cache_clear()

def analyze_graph(database):
    c = database.cursor()

    def init_results():
        global result
        result = [set() for _ in range(args.amnt)]

    def add_result(thisresult):
        global result
        i = len(result) - 1

        while i >= 0 and len(result[i]) < len(thisresult):
            i -= 1

        if i < len(result) - 1:
            result.insert(i + 1, thisresult)
            result.pop()

    def get_bound():
        return len(result[-1])

    def get_vertex_list():
	    return set(row[0] for row in c.execute('SELECT id FROM pages'))

    @functools.lru_cache(maxsize=131072, typed=False)
    def get_children(parent):
        l1 = set(t for f,t in c.execute('SELECT fromid, toid FROM cons WHERE fromid = ?', (parent,)) )
        l2 = set(f for f,t in c.execute('SELECT fromid, toid FROM cons WHERE toid = ?', (parent,)) )
        return l1 & l2

    def BronKerbosch2movingbound(R, P, X, depth=0):
        if len(R) + len(P) < get_bound():
            return
        if not P and not X:
            add_result(R)
            return
        next_info = args.info
        pivotset = P | X
        u = pivotset.pop()

        for count, v in enumerate(P - get_children(u)):
            if count >= next_info:
                next_info += args.info
                if not depth:
                    print('Searching for Cliques', round(count / (len(P)+len(X))*100,2), '%' )
            n = get_children(v)
            if len(n) >= get_bound():
                BronKerbosch2movingbound(R | set([v]), P & n, X & n, depth + 1)
            P.remove(v)
            X.add(v)

    init_results()
    print('Retrieving list of all pages')
    v = get_vertex_list()
    print('done')
    BronKerbosch2movingbound(set(), v, set())

def print_results(database):
    c = database.cursor()

    def get_name(i):
        try:
            return set(get_name(a) for a in i)
        except:
            row = next(c.execute('SELECT * FROM pages WHERE id = ?', [i]))
            return row[1]
    for count, res in enumerate(result):
        print(count, 'Result of length', len(res), ':\n', ', '.join(get_name(res)))

if __name__ == "__main__":
    parse_args()
    xmlp = get_xml_parser(args.xmlfile)
    conn = init_db()
    create_graph(xmlp, conn, args.xmlfile)
    analyze_graph(conn)
    print_results(conn)
    cleanup()
