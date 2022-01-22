import nltk


try:
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('averaged_perceptron_tagger')

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
