import requests
import csv
import os
import re
import bs4
import urllib
import pickle
import re
import glob
import numpy as np
from tqdm import trange

from util import GSD_Definition, GSD_Word

url = 'https://greensdictofslang.com/search/basic?q='
baseURL = 'https://greensdictofslang.com'

currentDir = os.path.dirname(__file__)

re_beginparen = re.compile(r"^\([^\)]*\)\s+")
re_endparen = re.compile(r"\s+\([^\)]*\)\W*$")
re_endpunc = re.compile(r"\W*$")
re_multispace = re.compile(r"\s+")

re_eg = re.compile(r"e\.g\..*$")
re_inphrs = re.compile(r"in phrs\..*$")
re_phr = re.compile(r"phr\..*$")
re_var = re.compile(r"var\..*$")
re_vars = re.compile(r"vars\..*$")
re_abbr = re.compile(r"abbr\..*$")
re_set_long = [re_eg, re_inphrs, re_phr, re_var, re_vars, re_abbr]

re_see = re.compile(r"see\s*$")
re_usu = re.compile(r"usu\s*$")
re_a = re.compile(r"a\s*$")
re_the = re.compile(r"the\s*$")
re_for = re.compile(r"for\s*$")
re_set_trail = [re_see, re_usu, re_a, re_the, re_for]

re_paren = re.compile(r"\(|\)")

re_dateslash = re.compile(r"\\xe2\\x80\\x93.*$")
re_datecomma = re.compile(r"\,.*$")
re_datefwdslash = re.compile(r"\/.*$")
re_dateslash2 = re.compile(r"\-.*$")
re_begindot = re.compile(r"^.*\.")
re_endchar = re.compile(r"(s|\?)$")
re_beginchar = re.compile(r"^\?")

re_cxt_hex = re.compile(r"\\x[0-9a-f][0-9a-f]")

punctuations = '!\'"#$%&()\*\+,-\./:;<=>?@[\\]^_`{|}~'

re_punc = re.compile(r"["+punctuations+r"]+")
re_space = re.compile(r" +")

re_extract_quote = re.compile(r"[1-9/]+:")
re_extract_quote_all = re.compile(r"[1-9/]+:.*$")

n_word = 0
n_def = 0

def proc_def(word, defsent_tag, quote_tag):
    senseno_tag = defsent_tag.find('span', class_='senseno')
    if senseno_tag is not None:
        senseno_tag.decompose()

    xref_tags = defsent_tag.find_all('a', class_='xref')
    for xref_tag in xref_tags:
        xref_tag.decompose()

    if not word.is_abbr():
        i_tags = defsent_tag.find_all('i')
        for i_tag in i_tags:
            i_tag.decompose()

    def_sent = defsent_tag.get_text().strip().replace('\\xe2\\x80\\x98', "'").replace('\\xe2\\x80\\x99', "'")
    def_sent = re_multispace.sub(' ', def_sent)
    def_sent = re_beginparen.sub('', def_sent)
    def_sent = re_endparen.sub('', def_sent)
    for r in re_set_long:
        def_sent = r.sub('', def_sent)
    def_sent = re_endpunc.sub('', def_sent)
    for r in re_set_trail:
        def_sent = r.sub('', def_sent)
    def_sent = re_endpunc.sub('', def_sent)
    def_sent = re_paren.sub('', def_sent)

    def_sent = def_sent.strip()

    if len(def_sent) > 0:
        w_def = GSD_Definition(def_sent)

        quote_tags = quote_tag.find_all('tr', class_='quotation')
        for q_tag in quote_tags:
            date_tag = q_tag.find('time')
            if date_tag is None:
                continue
            date = date_tag.get_text()
            if len(date) == 0:
                continue
            date = re_dateslash.sub('', date)
            date = re_dateslash2.sub('', date)
            date = re_datefwdslash.sub('', date)
            date = re_datecomma.sub('', date)
            date = re_begindot.sub('', date)
            date = re_endchar.sub('', date)
            date = re_beginchar.sub('', date)
            if date[0] == ' ':
                continue
            if date[-1] == ')':
                continue
            date = int(date)
            try:
                region = q_tag.find('td', class_="flag").find('img')['alt']
            except:
                continue

            if len(region) > 0:
                quote_sent_tag = q_tag.find('td', class_="quote")
                if quote_sent_tag is None:
                    w_def.add_stamp(date, region)
                else:
                    quote_sent = quote_sent_tag.get_text().strip()
                    quote_sent = re_cxt_hex.sub('', quote_sent)

                    quote_sent_proc = re_extract_quote_all.findall(quote_sent)
                    if len(quote_sent_proc) == 0:
                        w_def.add_stamp(date, region)
                    else:
                        quote_sent_proc = re_space.sub(' ', re_extract_quote.sub(' ', quote_sent_proc[0])).strip()
                        tokens = [s.lower() for s in re_space.sub(' ', re_punc.sub('', quote_sent_proc)).split(' ')]
                        if word.word.lower() in tokens:
                            w_def.add_stamp(date, region, quote_sent_proc)
                        else:
                            w_def.add_stamp(date, region)

        word.add_definition(w_def)


def tempFind(file):
    words = 0
    definitions = 0

    html_file = open('htmls/' + file, 'r')
    soup = bs4.BeautifulSoup(html_file.read(), "html.parser")

    head_tag = soup.find('h2', class_='head')
    w_word = head_tag.find('span', class_='hw').get_text()
    pos_tag = head_tag.find('span', class_='pos')
    if pos_tag is None:
        return [0, 0]
    w_pos = pos_tag.get_text()

    w_homonym = 0
    homonym_tag = head_tag.find('sup', class_='homonym')
    if homonym_tag is not None:
        homonym_text = homonym_tag.get_text()
        w_homonym = int(homonym_text)

    word = GSD_Word(w_word, w_pos, w_homonym)

    entry_tag = soup.find('article', class_="entry cited")
    def_tags = entry_tag.find_all('section', class_='definition', recursive=False)
    subdef_tags = entry_tag.find_all('section', class_='subdefinition', recursive=False)


    for i, def_tag in enumerate(def_tags):
        quote_tag = def_tag.find('section', class_='quotations qhidden')
        if quote_tag is None:
            quote_tag = def_tag.find('section', class_='quotations qshown')
            if quote_tag is None:
                continue
        defsent_tag = def_tag.find('p', id="sn"+str(i+1))
        if defsent_tag is None:
            continue
        proc_def(word, defsent_tag, quote_tag)

    for i, subdef_tag in enumerate(subdef_tags):
        defsent_tags = []
        quote_tags = []
        tags = subdef_tag.find_all(recursive=False)
        j = 0
        while j < len(tags):
            if tags[j].name == 'p':
                if j+1 == len(tags):
                    break
                if tags[j+1].name == 'section':
                    if tags[j+1]['class'] == ['quotations', 'qhidden'] or tags[j+1]['class'] == ['quotations', 'qshown']:
                        defsent_tags.append(tags[j])
                        quote_tags.append(tags[j+1])
                        j+=1
            j+=1
        for i in range(len(quote_tags)):
            proc_def(word, defsent_tags[i], quote_tags[i])

    if word.valid():
        words += 1
        definitions += word.num_def()

        with open('pickles/'+file+'.pickle', 'wb') as outfile:
            pickle.dump(word, outfile)
        
    return [words, definitions]



with open(os.path.split(currentDir)[0] + '/word_lists/us_uk.csv') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    for row in csv_reader:
        print('getting ' + row[0] + ' pages')
        index = 0
        r = requests.get(url + row[0], allow_redirects=True)
        html = r.content.decode()
        for n in range(0, int(row[1])):
            index = html.find('href="/entry/', index)
            if index == -1:
                break
            extension = html[index+6:index+20]
            page = extension[7:]
            r = requests.get(baseURL+extension, allow_redirects=True)
            open('htmls/' + page + '.html', 'w').write(str(r.content))
            w, d = tempFind(page + '.html')
            n_word += w
            n_def += d
            index += 21


with open(os.path.split(currentDir)[0] + '/word_lists/us_uk_aus.csv') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    for row in csv_reader:
        print('getting ' + row[0] + ' pages')
        index = 0
        r = requests.get(url + row[0], allow_redirects=True)
        html = r.content.decode()
        for n in range(0, int(row[1])):
            index = html.find('href="/entry/', index)
            if index == -1:
                break
            extension = html[index+6:index+20]
            page = extension[7:]
            r = requests.get(baseURL+extension, allow_redirects=True)
            open('htmls/' + page + '.html', 'w').write(str(r.content))
            w, d = tempFind(page + '.html')
            n_word += w
            n_def += d
            index += 21


print('there are ' + str(n_word) + ' words')
print('there are ' + str(n_def) + ' definitions')