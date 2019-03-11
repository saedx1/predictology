import xml.etree.ElementTree as ET
import itertools
import string
import codecs
import os
import pandas as pd
import sys
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize, WhitespaceTokenizer

def getSentences(txtdata):
    lines = txtdata.split('\n')
    sentences = []
    for line in lines:
        sentences += sent_tokenize(line)
    return sentences

def getWords(sentence):
    return word_tokenize(sentence)

def getFilesLists():
    textFiles = os.listdir(textFolder)
    xmlFiles = os.listdir(xmlFolder)
    return textFiles, xmlFiles

def is_encoded(encoding, start, end, word):
    encodings = []
    for key, val in encoding:
        if val['start'] <= start and val['end'] >= end and word in val['text']:
            encodings.append((val['code'], start != val['start'] or end != val['end']))
    if len(encodings) == 0:        
        return ('O', False)
    elif len(encodings) == 1:
        return encodings[0]
    else:
        if len(encodings) > 2:
            print "More than one annotation\n\tWord = {}".format(word)
            return ('XXXXXX',False)
        if encodings[0][1]:
            return encodings[0]
        return encodings[1]

## RUN THOSE TWO LINES IF IT FAILS
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')

def processFile(xmlroot, fname):
    encoding = dict()
    for tag in xmlroot.iter('classMention'):
        idx = tag.get('id')
        encoding[idx] = dict()
        for child in tag:
            if child.tag != 'mentionClass':
                continue
            encoding[idx]['code'] = child.get('id')
            encoding[idx]['as'] = child.text
            break
    for tag in xmlroot.iter('annotation'):
        start = end = None
        for child in tag:
            if child.tag == 'mention':
                idx = child.get('id')
            elif child.tag == 'spannedText':
                text = child.text
            elif child.tag == 'span':
                if start is None:
                    start, end = (int(child.get('start')), int(child.get('end')))
                else:
                    start, end = (min(start, int(child.get('start'))), max(end, int(child.get('end'))))

        encoding[idx]['text'] = text
        encoding[idx]['start'] = start
        encoding[idx]['end'] = end
    # for limit, text, inst in itertools.izip(xmlroot.iter('span'), xmlroot.iter('spannedText'), xmlroot.iter('mention')):
    #     idx = inst.get('id')
    #     encoding[idx]['text'] = text.text
    #     encoding[idx]['start'] = int(limit.get('start'))
    #     encoding[idx]['end'] = int(limit.get('end'))

    encoding = encoding.values()
    temp = []
    for i in encoding:
        text = i['text']
#         i.pop('text')
        temp.append((text,i))
    encoding = temp[:]

    sentences = getSentences(txtdata)
    sentence_encoding = []
    sent_before = 0

    for sent in sentences:
        sent_start = txtdata.find(sent, sent_before)
        sent_end = sent_start + len(sent)
        word_before = 0

        temp = []
        more = 0
        words = getWords(sent)
        poss = nltk.pos_tag(words)
        for word, pos in zip(words, [x[1] for x in poss]):
            word_start = sent_start + sent.find(word, word_before)
            word_end = word_start + len(word)
            
            enc, tmp_more = is_encoded(encoding, word_start, word_end, word)
            if enc == 'XXXXXX':
                print '\tArticle = %s' % fname
                enc = 'O'
                
            if tmp_more:
                more += 1
#                 temp.append((word, 'O', pos))
                if more == 1:
                    temp.append((word, 'B-' + enc, pos))
                else:
                    temp.append((word, 'I-' + enc, pos))

#                 temp.append((word, enc, pos))
            else:
                more = 0
                temp.append((word, ('' if enc == 'O' else 'B-') + enc, pos))

            word_before = word_end - sent_start

        sentence_encoding.append(temp)
        sent_before = sent_end
    return sentences, sentence_encoding

if len(sys.argv) != 5:
    print "Command should be: %s [XMLInputFolder] [FullXMLExtension] [ArticlesTextFolder] [CSVOutputFile] " % sys.argv[0]
    exit(0)

xmlFolder = sys.argv[1]
xmlext = sys.argv[2]
textFolder = sys.argv[3]

data = []
cnt = 0
allfiles = [i for i in os.listdir(textFolder) if i.endswith('.txt')]
total = len(allfiles)
done = 0
for myfile in allfiles:
    xmlfile = tree = ET.parse(os.path.join(xmlFolder, myfile + xmlext))
    xmlroot = xmlfile.getroot()
    txtdata = codecs.open(os.path.join(textFolder, myfile), 'r', encoding='utf8').read()
    sentences, sentence_encoding = processFile(xmlroot, myfile)
    for i in range(len(sentence_encoding)):
        kk = 0
        for word, code, pos in sentence_encoding[i]:
        #             data.loc[cnt] = [myfile, i, word, code]
            data.append((myfile, i, word.encode('utf-8').strip(), kk, pos, code))
            kk += 1
            cnt += 1
    done += 1
    print 'Finished {}/{} Files!\r'.format(done, total),
    sys.stdout.flush()

data_df = pd.DataFrame(data, columns=['article','sentence_no', 'word', 'word_no', 'part_of_speech', 'encoding'])
data_df.to_csv(sys.argv[4], index=False)

