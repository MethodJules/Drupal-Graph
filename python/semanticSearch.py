from neo4j import GraphDatabase
import json
import re
import unidecode
import spacy
from annoy import AnnoyIndex
import os




driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "test"), encrypted=False)

session = driver.session()



# Beim Starten der Anwendung Spacy in den Arbeitsspeicher laden. Damit dieser Vorgang schneller geht, werden die Teilmodule tagger und ner nicht geladen, da diese nicht benötigt werden.
nlp = spacy.load('en_core_web_lg', disable=["tagger", "ner"])

# Standardmäßig sind die Stop Words in Spacy nicht aktiviert. Die Aktivierung muss einmal durchgeführt werden.
for word in nlp.Defaults.stop_words:
    lex = nlp.vocab[word]
    lex.is_stop = True

text = "who immigrated to palestine and promoting social work"

if (len(text) > 0):
    msg_arr = {}
    # Bestimmte Zeichen entfernen. Text in Klammern wird komplett entfernt.
    text = text.strip()
    text = re.sub(r'\([^()]*\)', '', text)
    text = text.replace('"', '')
    text = text.replace('“', '')
    text = text.replace("‘", '')
    text = text.replace("’", '')
    text = text.replace("”", '')
    text = text.replace("'", '')
    text = text.replace('/', ' ')
    text = text.replace("  ", " ")
    text = unidecode.unidecode(text)
    for word in nlp.Defaults.stop_words:
        lex = nlp.vocab[word]
        lex.is_stop = True

    result_list = []
    doc = nlp(text.lower())
    # Alle Stop Words entfernen und die verbleibenden Wörter lemmatisieren, sodass die Ursprungsform in dem Array steht. In der Datenbank sind die Tags
    # ebenfalls lemmatisiert und können so miteinander verglichen werden
    shorten_doc = nlp(' '.join([str(t) for t in doc if not t.is_stop]))
    shorten_doc_lemma_list = []
    shorten_doc_lemma = ""
    for token in shorten_doc:
        # Punkte, Kommata etc. nicht mit berücksichtigen
        if (token.lemma_ not in ['.', ',', ';', '-']):
            shorten_doc_lemma_list.append(token.lemma_)
            shorten_doc_lemma += token.lemma_ + " "

    shorten_doc_lemma = shorten_doc_lemma.replace('  ', ' ').strip()
    print(shorten_doc_lemma)

if (len(shorten_doc_lemma_list) > 0):
    try:
        # Neues Spacy Doc aus dem gekürzten und lemmatisierten Suchstring erzeugen
        doc = nlp(shorten_doc_lemma)
        # Den Suchindex laden. In diesem sind alle Vektoren der Sentences und Clauses zusammen mit der ID des Hauptknoten abgespeichert.
        ann = AnnoyIndex(300)
        ann.load('search_index.ann')
        # Den Vektor vom Suchstring übergeben und die 50 nächsten Nachbarn anhand der Vektoren zurückgeben.
        similar_ids = ann.get_nns_by_vector(doc.vector, 50)
        print('Similiar IDs')
        print(similar_ids)
        if (len(similar_ids) > 0):
            # Konfigurationsdatei laden und Similarity Score auslesen
            try:
                file_path = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(file_path, 'config.json')
                file = open(config_path, 'r', encoding="utf8")
                data = file.read()
                config = json.loads(data)
            except:
                raise
            similarity_score = float(config['similarity_score'])
            # Die Informationen 50 nächsten Sätze aus dem Suchindex aus der Datenbank laden
            result = get_sent_clauses_by_id(similar_ids)
    except Exception as e:
        print(e)