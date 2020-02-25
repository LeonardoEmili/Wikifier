import bz2
import nltk
import numpy as np
import json
import re
from collections import Counter
nltk.download('punkt')

train_file = bz2.BZ2File('../input_data/train.json.bz2')
train_file = json.load(train_file)
train_links = []
LINK_DELIM = "_"

#print(train_file[412118])
#print(train_file[7144])

for i in range(len(train_file)):
    sentence, link = next(iter(train_file[i].items()))
    train_file[i] = sentence.lower().strip()
    if (LINK_DELIM in train_file[i]):
        print("Errore {}".format(i))
    if link is not None:
        train_file[i] = LINK_DELIM + LINK_DELIM.join(filter(None, train_file[i].split())) + LINK_DELIM
        train_links.append(link)

output = train_links + ["_TEXT"]
link2idx = {l:i for i,l in enumerate(output)}
idx2link = {i:l for i,l in enumerate(output)}
default_no_link = len(output) -1

labels = []
train_sentences = []
index = 0

train_file = [[word for word in nltk.word_tokenize(sentence)] for sentence in nltk.sent_tokenize(" ".join(train_file))]

print(len([word for sentence in train_file for word in sentence if word[0]==LINK_DELIM and word[-1]==LINK_DELIM]))
print(len(train_links))
#for sentence in nltk.sent_tokenize(" ".join(train_file)):
    #label = []
    #train_sentence = []
    #for word in nltk.word_tokenize(sentence):
        #if word[0] == "_" and word[-1] == "_":
            #sub_links = word.split("_")
            #for sub_link in sub_links:
                #train_sentence.append(word)
                #label.append(idx2link[index])
            #index += 1
        #else:
            #train_sentence.append(word)
            #label.append(default_no_link)
    #labels.append(label)
    #train_sentences.append(train_sentence)