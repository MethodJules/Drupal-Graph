import spacy
import subprocess
import os
import re
import json
from StanfordConnectClass import StanfordConnect
from builtins import str, object
from neo4jClass import neo4jConnector
import shutil
import datetime
from nltk.corpus import wordnet
import unidecode
from annoy import AnnoyIndex


class nlpProcess(object):

    nlp = None
    driver = None
    dir_path = os.path.dirname(os.path.realpath(__file__))

    # Beim Instanziieren wird Spacy geladen und die standardmäßig deaktivierten Stop Words aktiviert
    def __init__(self):
        '''
        Constructor
        '''
        self.nlp = spacy.load('en_core_web_lg', disable=["tagger", "ner"])

        for word in self.nlp.Defaults.stop_words:
            lex = self.nlp.vocab[word]
            lex.is_stop = True

    # Die Funktion extrahiert die Informationen wie Tags, Synonyme, Entitäten etc. aus dem Text
    def extractInformations(self, text):

        # Unnötige Zeichen entfernen. Jeglicher Text in Klammern wird entfernt
        text = re.sub(r'\([^()]*\)', '', text)
        text = text.replace('"', '')
        text = text.replace('“', '')
        text = text.replace("‘", '')
        text = text.replace("’", '')
        text = text.replace("”", '')
        text = text.replace("'", '')
        text = text.replace('/', ' ')
        text = text.replace("  ", " ")

        # Spacy Objekt erzeugen, sodass einzelne Sätze iteriert werden können
        doc = self.nlp(text)

        # Variablen initialisieren
        result = {}
        extract_dict = {}
        extract_dict['sent_clauses'] = {}
        sent_counter = 0

        # Informationen für den Parser ClausIE festelegen
        #parser_info = ['java', '-jar',
        #             self.dir_path + '/ClausIE/clausie.jar','-c',
        #             self.dir_path + '/ClausIE/resources/clausie.conf',
        #             '-v', '-s']

        parser_info2 = 'java -jar ' + self.dir_path + '/ClausIE/clausie.jar -c ' + self.dir_path + '/ClausIE/resources/clausie.conf -v -s'

        # Alle Sätze des Dokuments iterieren
        for sent in doc.sents:

            # extract_dict anfangen zu initialsieren. In diesem Wörterbuch stehen zum Schluss alle Sätze mit ihren Teilsätzen
            # einzelnen Tags oder auch Token, Synonyme, Entitäten und Relationen drin
            extract_dict['sent_clauses'][sent_counter] = {}
            extract_dict['sent_clauses'][sent_counter]['clauses'] = {}
            extract_dict['sent_clauses'][sent_counter]['tags'] = {}
            extract_dict['sent_clauses'][sent_counter]['original_sent'] = sent.text

            # Alle unnötigen stop words entfernen. Dies sind Füllwörter wie "was", "is", "and", etc. Für die Suche mit semantischer Ähnlichkeit würden
            # diese nur das Ergebnis verfälschen, da diese häufiger in Sätzen vorkommen
            shorten_sent = self.nlp(' '.join([str(t) for t in sent if not t.is_stop]))

            shorten_lemma_original = ""

            tag_counter = 0

            # Alle Token des gekürzten Satzes iterieren
            for token in shorten_sent:

                # Zeichen wie Punkte, Kommata, etc. nicht berücksichtigen
                if (token.lemma_ not in ['.', ',', ';', '-']):

                    # Aus dem gekürzten Satz werden die Lemma der Token geholt, sodass aus z.B. born die Grundform bear wird.
                    # Bei jeder Suchanfrage wird ebenfalls jedes Token lemmatisiert und somit können die einzelnen Wörter in ihrer Grundform miteinander verglichen werden
                    shorten_lemma_original += token.lemma_ + " "

                    extract_dict['sent_clauses'][sent_counter]['tags'][tag_counter] = {}
                    extract_dict['sent_clauses'][sent_counter]['tags'][tag_counter]['label'] = token.lemma_
                    extract_dict['sent_clauses'][sent_counter]['tags'][tag_counter]['synonyms'] = {}

                    # Für jedes Token werden Synonyme geholt
                    synonyms = list()
                    synset = wordnet.synsets(token.lemma_)

                    # In den Synsets können Synonyme doppelt vorkommen oder auch das Token wird als Synonym von sich selber angegeben. Solche Einträge sollen nicht mit aufgenommen werden
                    for synset in synset:
                        for lemma in synset.lemmas():
                            if (lemma.name() != token.lemma_):
                                if (lemma.name() not in synonyms):
                                    synonyms.append(lemma.name().replace('_', ' '))

                    # Nur die ersten 6 Synonyme zum Wörterbuch hinzufügen. Dient einfach nur der Limitierung, dass ein Token nicht dutzende von Synonymen hat
                    syn_counter = 0
                    for syn in synonyms:
                        if (syn_counter < 6):
                            extract_dict['sent_clauses'][sent_counter]['tags'][tag_counter]['synonyms'][syn_counter] = syn.replace('"', '').replace("‘", '').replace("’", '').replace("'", '').replace("  ", " ")
                        syn_counter += 1

                    tag_counter += 1

            # Neben dem Originalsatz auch den gekürzten lemmatisierten Satz hinzufügen
            extract_dict['sent_clauses'][sent_counter]['shorten_lemma_original'] = shorten_lemma_original.replace("  ", "").strip()
            #print(extract_dict)


            # Nun werden alle Sätze mit ClausIE untersucht, um Teilsätze zu extrahieren. Damit funktioniert Stanford CoreNLP besser
            # Da ClauIE ein eigenständiges Java Programm ist, muss ein Prozess erstellt und jeder Satz zur Analyse hingeschickt werden
            cmd = subprocess.Popen(parser_info2, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)

            try:
                cmd.stdin.write(unidecode.unidecode(sent.text))
            except UnicodeEncodeError as e:
                cmd.stdin.write(unidecode.unidecode(sent.text))

            stdout = cmd.communicate()
            clause_counter = 0

            # Teilsätze von ClausIE extrahieren und im Wörterbuch speichern, sowie auch die gekürzte lemmatisierte Form des Teilsatzes
            for line in stdout[0].splitlines():
                if (line[0] == "1"):
                    clause = line.replace('1\t"', "").replace('"\t"', ' ').replace('"', '')
                    existing = False
                    for key,value in extract_dict['sent_clauses'][sent_counter]['clauses'].items():
                        if (clause in value['original_clause']):
                            existing = True
                            break

                    if (existing == False):
                        clause_nlp = self.nlp(clause)
                        shorten_clause = self.nlp(' '.join([str(t) for t in clause_nlp if not t.is_stop]))

                        if (len(shorten_clause) > 1):
                            extract_dict['sent_clauses'][sent_counter]['clauses'][clause_counter] = {}
                            extract_dict['sent_clauses'][sent_counter]['clauses'][clause_counter]['original_clause'] = clause + '.'

                            shorten_lemma_clause = ""
                            for token in shorten_clause:
                                if (token.lemma_ not in ['.', ',', ';', '-']):
                                    shorten_lemma_clause += token.lemma_ + ' '
                            extract_dict['sent_clauses'][sent_counter]['clauses'][clause_counter]['shorten_lemma_clause'] = shorten_lemma_clause.strip().replace("  ", "")
                    clause_counter += 1
            sent_counter += 1

            #------------------------

        clauses_merged = ""

        # Stanford CoreNLP arbeitet am besten mit kompletten Texten, um Coreference etc. besser anwenden zu können.
        # Dafür werden die extrahierten Teilsätze zu einem Text zusammengefügt. Da ein Satz nun aber aus mehreren Teilsätzen bestehen kann
        # und später aber extrahierte Entitäten etc. dem gesamten Satz zugeordnet werden sollen, wird nach allen Teilsätzen eines Satzes
        # ein Platzhalter [[1]] mit der Satznummer eingefügt.
        for key, value in extract_dict['sent_clauses'].items():
            clauses_merged += "[[" + str(key) + "]]. "
            if (len(value['clauses'].items()) > 0):
                for key2, value2 in value['clauses'].items():
                    clauses_merged += value2['original_clause'] + " "
            else:
                # Wurden keine Teilsätze extrahiert den kompletten Satz verwenden
                clauses_merged += value['original_sent']


        #print (clauses_merged)
        # URL und Port aus der Config lesen. Schlägt dies Fehl eine Exception werfen, die das Programm beendet
        corenlp_url = ''
        corenlp_port = ''
        try:
            file_path = os.path.dirname(os.path.abspath(__file__))

            filename = os.path.join(file_path, 'config.json')
            file = open(filename, 'r', encoding="utf-8")
            data = file.read()
            config = json.loads(data)

            corenlp_url = config['corenlp_url']
            corenlp_port = config['corenlp_port']
        except:
            raise


        # Mit Stanford CoreNLP verbinden und den zusammengesetzten Text zur Analyse schicken
        nlp = StanfordConnect(corenlp_url, port=corenlp_port)

        props={'timeout': '300000',
               'annotators': 'tokenize,ssplit,pos,ner,kbp',
               'pipelineLanguage':'en',
               'outputFormat': 'json'
               }


        result = nlp.annotate(clauses_merged, properties=props)

        # Versuchen das Json in ein Array zu laden. Ansonsten brauch nicht weiter fortgefahren werden
        try:
            result_dict = json.loads(result)
        except:
            raise RuntimeError(result)

        extract_dict['entities'] = {}
        extract_dict['relations'] = {}

        # Bei den Entitäten können auch Pronomen mit auftauchen. Die Liste wird definiert, damit im weiteren Verlauf die Entitäten abgeglichen
        # werden können und Pronomen nicht übernommen werden
        pronouns = ['he', 'she', 'it', 'we', 'they', 'theirs', 'ours', 'hers', 'his', 'its', 'her', 'his', 'their', 'our', 'him']

        # Alle Sätze iterieren, die Stanford CoreNLP zurückliefert. Zu jedem Satz existiert ein Array mit Entitäten und Relationships
        for sen in result_dict['sentences']:

            # Der Platzhalter [[1]] wurde von CoreNLP in seine Bestandteile zerlegt. Jeder Teilsatz wurde von CoreNLP wiederum als eigener Satz
            # abgespeichert und zurückgegeben. Damit nun überprüft werden kann, ob der nächste Platzhalter gearde beim Iterieren getroffen wurde
            # werden die Token von einem Satz des Ergebnisarrays zusammengesetzt.
            sent_token = ""
            for token in sen['tokens']:
                sent_token += token["originalText"]

            sent_number = re.search("\[\[(.*?)\]\]", sent_token)

            # Wurde der Platzhalter getroffen, wird der Zähler für die ursprünglichen Sätze um eins hochgezählt und der Counter für die Entitäten
            # und Relationships zurückgesetzt. Auch wenn bis dahin aus dem Ergebnisarray bereits x Sätze iteriert wurden, so waren das nur die
            # Teilsätze. Später sollen aber alle Entitäten von Teilsätzen, die zu einem Satz gehören, dem ursprünglichen Satz zugeordnet werden können
            if (sent_number != None):
                sen_count = int(sent_number.group(1))
                extract_dict['entities'][sen_count] = {}
                extract_dict['relations'][sen_count] = {}
                en_count = 0
                rel_count = 0
                continue

            # Alle Entitäten für einen Teilsatz auslesen und im Wörterbuch speichern, aber nur wenn diese nicht bereits im Wörterbuch beim entsprechenden Satz vorhanden sind
            for ent in sen['entitymentions']:

                if (ent['text'].lower().strip() not in pronouns):

                    existing = False
                    for key,value in extract_dict['entities'][sen_count].items():
                        if (value['text'] == ent['text'] and value['ner'] == ent['ner']):
                            existing = True

                    if (existing == False):
                        extract_dict['entities'][sen_count][en_count] = {}
                        extract_dict['entities'][sen_count][en_count]['text'] = ent['text']
                        extract_dict['entities'][sen_count][en_count]['ner'] = ent['ner']
                        en_count += 1

            # Alle Relationships für einen Teilsatz auslesen und im Wörterbuch speichern, aber nur wenn diese nicht bereits im Wörterbuch beim entsprechenden Satz vorhanden sind
            for kbp in sen['kbp']:

                existing = False
                for key,value in extract_dict['relations'][sen_count].items():
                    if (value['subject'] == kbp['subject'] and value['relation'] == re.sub(r'.*?\:', '', kbp['relation']) and value['object'] == kbp['object']):
                        existing = True

                if (existing == False):
                    extract_dict['relations'][sen_count][rel_count] = {}
                    extract_dict['relations'][sen_count][rel_count]['subject'] = kbp['subject']

                    # Alle Relationships fangen immer beispielsweise so an: PER:city_of_birts. Alles vor dem : wird entfernt
                    extract_dict['relations'][sen_count][rel_count]['relation'] = re.sub(r'.*?\:', '', kbp['relation'])
                    extract_dict['relations'][sen_count][rel_count]['object'] = kbp['object']

                    for sen2 in result_dict['sentences']:
                        for ent in sen2['entitymentions']:
                            # Bei den KBP Relationships steht nicht named entity recognition (ner) wie CITY, COUNTRY etc. dabei. Hier werden die ner Werte
                            # aus den bereits gesammelten Entiäten ausgelesen, um diese bei den Relationships mit zu speichern
                            if (kbp['subject'] == ent['text']):
                                extract_dict['relations'][sen_count][rel_count]['subject_ner'] = ent['ner']
                            if (kbp['object'] == ent['text']):
                                extract_dict['relations'][sen_count][rel_count]['object_ner'] = ent['ner']

                    rel_count += 1

        return extract_dict

    # Funktion fügt einen neuen Eintrag in die Log-Datei mit genauer Zeitangabe hinzu
    def add_log(self, message):

            now = datetime.datetime.now()

            message = (now.strftime("%Y-%m-%d %H:%M:%S")) + ': ' + message + '\n'

            file_path = os.path.dirname(os.path.abspath(__file__))

            filename = os.path.join(file_path, 'nlplog.log')
            f = open(filename, "a", encoding="utf-8")
            f.write(message)
            f.close()

    # Diese Funktion ist der Einstiegspunkt der Klasse. In ihr werden die exportieren Nodes von Drupal aus der json-Datei geladen und zu jeder Node
    # wird die Funktion extract_information() aufgerufen. Die Funktion ruft sich rekursiv auf und arbeitet immer die oberste Node einen Content Types ab und entfernt
    # anschließend die Node aus der Datei, wenn die Informationen extrahiert und in der DB gespeichert wurden.
    def start_extraction(self):
        print('Start extraction')

        file_path = os.path.dirname(os.path.abspath(__file__))


        file_name_process = os.path.join(file_path, 'export/nodes_export_process.json')

        text_arr = None

        # Für das Abarbeiten von Nodes aus der Datei nodes_export.json wird diese Datei zu nodes_export_process.json kopiert. Somit können aus Drupal heraus Nodes
        # exportiert werden, während aus der Datei nodes_export_process.json noch Nodes verarbeitet werden und es wird nicht in derselben Datei von unterschiedlichen
        # Prozessen zeitgleich Inhalt hinzugefügt, bzw. entfernt. Da die Funktion rekursiv aufgerufen wird, wird jedes mal überprüft, ob die nodes_export_process.json
        # noch existiert und der Inhalt per json.loads geladen werden kann.
        if (os.path.isfile(file_name_process)):
            try:
                file = open(file_name_process, 'r', encoding="utf-8")
                data = file.read()
                file.close()

                if (data == ''):
                    os.remove(file_name_process)

            except:
                self.add_log("Problem opening file " + file_name_process)
                self.add_log("exit Task")
                exit()

            try:
                text_arr = json.loads(data)

                # Ist die Länge des Arrays 0, so wurden alle Nodes abgearbeitet und die Datei kann gelöscht werden
                if (len(text_arr) == 0):
                    self.add_log('File ' + file_name_process + ' is empty. Delete file.')
                    os.remove(file_name_process)
                    text_arr = None
            except:
                self.add_log("Cant convert data from " + file_name_process + ' into json dict')

        # Wurde kein Json bis hier geladen oder die Datei nodes_export_process.json existiert nicht mehr, so wird die Datei nodes_export.json
        # versucht zu öffnen
        if(text_arr == None):

            file_name_default = os.path.join(file_path, 'export/nodes_export.json')

            try:
                file = open(file_name_default, 'r', encoding="utf-8")
                data = file.read()
                json_arr = json.loads(data)

                # Ist diese Datei leer, weil aktuell keine Nodes verarbeitet werden müssen, wird die Anwendung beendet
                if (len(json_arr) == 0):
                    self.add_log("No input for processing in " + file_name_default)
                    self.add_log("exit Task")
                    exit();
            except:
                self.add_log("No input for processing in " + file_name_default)
                self.add_log("exit Task")
                exit();

            try:
                # Sind Nodes in der Datei, dann wird diese in nodes_export_process.json kopiert, mit der dann beim nächsten rekursiven Aufruf
                # weiter gearbeitet wird
                shutil.copy2(file_name_default, file_name_process)

                self.add_log("Copy file " + file_name_default + " to " + file_name_process)

                # Da die Datei kopiert wurde, kann die Ausgangsdatei nun geleert und gespeichert werden.
                file = open(file_name_default, "w")
                file.write("{}")
                file.close()

                # Inhalt aus der neuen Datei auslesen und in data speichern
                file = open(file_name_process, 'r', encoding="utf-8")
                data = file.read()
                file.close()
            except:
                self.add_log("Problem opening file " + file_name_process)
                self.add_log("exit Task")
                exit()

            # Versuchen json zu laden. Schlägt dies fehl, soll die gesamte Anwendung beendet werden, da es keine Daten zum Verarbeiten gibt
            try:
                text_arr = json.loads(data)
            except:
                self.add_log("Cant convert data from " + file_name_process + ' into json dict')
                self.add_log("exit Task")
                exit();

        # Fehlgeschlagene Nodes werden in einer Datei gespeichert. Damit weitere fehlgeschlagene Nodes hinten angehängt werden können, die Datei zunächst erst einmal laden.

        failed_nodes_name = os.path.join(file_path, 'export/nodes_failed.json')
        failed_nodes_arr = None

        if (os.path.isfile(failed_nodes_name)):
            f = open(failed_nodes_name, "r", encoding="utf-8")
            data = f.read()
            f.close()

            if (data == ''):
                failed_nodes_arr = {}
            else:
                try:
                    failed_nodes_arr = json.loads(data)
                except:
                    failed_nodes_arr = {}
        else:
            failed_nodes_arr = {}


        # Durch den rekursiven Aufruf der Funktion wird pro Aufruf eine Node abgearbeitet. Dafür zunächst den obersten Content Type aus dem Array laden
        # In dem mehrdimensionalen Array vom Content Type als nächste die Node ID holen und die dazugehörigen Values
        content_type = next(iter(text_arr))
        content_type_values = next(iter(text_arr.values()))
        node_id = next(iter(content_type_values))
        node_values = next(iter(content_type_values.values()))

        title = node_values['title']
        created = node_values['created']
        changed = node_values['changed']

        self.add_log("Remaining Nodes: " + str(len(content_type_values.keys())))
        self.add_log("Node ID: " + node_id + "; Title: " + title)

        print("Remaining Nodes: " + str(len(content_type_values.keys())))
        print(node_id)

        # Versuchen die bisherige Node in Neo4j zu löschen. Dabei werden nicht Entitäten und Synonyme gelöscht, nur die Root Node
        # Content Fields, Sentence, Tags und die Relationen dazwischen. Beim erneuten indexieren einer Node und eventuellen Veränderungen
        # ist es einfacher den Baum, den die Node mit ihren Content Fields, Sentences etc. aufspannt einmal komplett zu entfernen.
        tries = 3
        for i in range(tries):
            try:
                self.driver.del_node(node_id)
            except Exception as e:
                if (type(e).__name__ == "ServiceUnavailable" and i < tries - 1):

                    self.add_log(str(e))
                    self.add_log("Retry")
                    continue
                else:
                    raise
            break

        # Alle Felder der aktuellen Node aus dem Array iterieren, versuchen die Informationen mit CoreNLP zu extrahieren und anschließend in Neo4j zu speichern.
        for field, content in node_values['fields'].items():

            # Manche Felder haben mehrere Inhalte (beispielsweise beim Feld Siblings wäre jedes aufgeführte Geschwisterkind ein eigener Inhalt) und Drupal gibt zu jedem
            # Feld ein Array mit den unterschiedlichen Inhalten zurück.
            for text in content:

                # Versuchen die Informationen zu extrahieren. Das Einfügen in Neo4j ergibt nur Sinn, wenn dieser Prozess erfolgreich war. Andernfalls wird die Node mit
                # den dazugehörigen Values in nodes_failed mit aufgenommen
                extract_success = False
                try:
                    extract_dict = self.extractInformations(text)
                    extract_success = True
                except RuntimeError as e:
                    if (content_type not in failed_nodes_arr):
                        failed_nodes_arr[content_type] = {}
                    failed_nodes_arr[content_type][node_id] = node_values
                    self.add_log("Problem occured during extraction. Maybe restart stanford core nlp. Message: " + str(e))
                    print('runtimereror')
                except Exception as e:

                    if (content_type not in failed_nodes_arr):
                        failed_nodes_arr[content_type] = {}
                    failed_nodes_arr[content_type][node_id] = node_values

                    self.add_log("Problem occured during extraction. Maybe restart stanford core nlp. Message: " + str(e))
                    print('generic error')

                # War das Extrahieren der Informationen erfolgreich, soll das Ergebnis in Neo4j abgespeichert werden. Auch hier gilt, wenn das
                # Abspeichern nicht möglich ist, wird die Node mit den Values in nodes_failed mit aufgenommen
                if (extract_success):
                    tries = 3
                    for i in range(tries):
                        try:

                            self.add_log("Insert field " + field + " with content in database")

                            print(self.driver.create_root_node(extract_dict, node_id, content_type, field, title, created, changed).data())
                            #self.driver.create_root_node(extract_dict, node_id, content_type, field, title, created, changed)
                        except Exception as e:

                            if (type(e).__name__ == "ServiceUnavailable" and i < tries - 1):
                                self.add_log(str(e))
                                self.add_log("Retry")
                                continue
                            else:
                                if (content_type not in failed_nodes_arr):
                                    failed_nodes_arr[content_type] = {}
                                failed_nodes_arr[content_type][node_id] = node_values

                                self.add_log("Problem occured during save. Maybe restart neo4j service. Message: " + str(e))


                        break


        # Egal ob das Extrahieren und Abspeichern erfolgreich war, soll im Anschluss die Node mit den Values aus dem Array entfernt werden, damit beim nächsten rekursiven
        # Aufruf die nächste Node mit ihren Values abgearbeitet werden kann
        del(text_arr[content_type][node_id])

        # Hat der Content Type keine Nodes mehr, so soll dieser auch entfernt werden, damit ggf. mit dem nächsten Content Type und seinen Nodes beim nächsten rekursiven
        # Aufruf fortgefahren werden kann.
        if(len(text_arr[content_type].keys()) == 0):
            del(text_arr[content_type])

        # Das Array mit den Content Types und Nodes wieder abspeichern
        file = open(file_name_process, "w", encoding="utf-8")
        file.write(json.dumps(text_arr))
        file.close()

        # Das Array mit den fehlgeschlagenen Nodes ebenfalls abspeichern
        file = open(failed_nodes_name, "w", encoding="utf-8")
        file.write(json.dumps(failed_nodes_arr))
        file.close()

        # Ist die Länge vom Array 0, wurden alle Content Types und Nodes abgearbeitet. Danach den Suchindex neu erstellen und manuell hinzugefügte Entitäten
        # zu den Bäumen in der Datenbank hinzufügen.
        if (len(text_arr) == 0):

            # Der Suchindex erleichtert das Durchsuchen der Sätze und Teilsätze für die semantische Ähnlichkeit. Werden jedes mal alle Sätze aus der Datenbank geladen
            # und auf semantische Ähnlichkeit überprüft werden, dauert ein Aufruf mehr als 10 Sekunden, da es tausende von Sätzen sind. Beim Suchindex werden die Vektoren der Sätze so im Suchindex abgespeichert,
            # sodass durch nearest neighbor search die ähnlichen Sätze gefunden werden können. Dadurh verringert sich die Zeit auf ms. Der Suchindex kann aber nicht aktualisiert werden
            # und muss daher jedes mal neu erstellt werden.
            result = self.driver.get_all_sent_clauses()

            if (len(result) > 0):

                self.add_log('Creating search index')
                ann = AnnoyIndex(300)

                for res in result:

                    nlp_res = self.nlp(res['shorten_original'].lower())
                    ann.add_item(int(res['sen_id']), nlp_res.vector)

                    counter = 0
                    for clause in res['shorten_clauses']:

                        clause_count = clause[1]
                        nlp_clause = self.nlp(clause[0].lower())
                        ann.add_item(int(clause_count), nlp_clause.vector)
                        counter += 1

                ann.build(10)
                ann.save('search_index.ann')

                # Die manuell hinzugefügten Entitäten stammen von Drupal und wurden nach dem Anlegen in eine Datei abgespeichert, die
                # von dieser Anwendung verarbeitet werden kann. Da beim erneuten Indexieren die Node mit ihren Unterknoten aus Neo4j gelöscht wird und somit keine Verbindung mehr mit
                # manuell hinzugefügten Entitäten besteht wird im Anschluss geschaut in welchen Sätzen der Nodes die entsprechenden Entitäten vorkommen und verknüpft diese mit den Sätzen.

                self.add_log('Adding manual created nodes')

                manually_entities = None
                try:
                    changed_entities = os.path.join(file_path, 'changed_entities.json')
                    file = open(changed_entities, 'r', encoding="utf-8")
                    data = file.read()
                    changed_entities = json.loads(data)
                    manually_entities = changed_entities['added_entities']
                except:
                    pass

                if (manually_entities != None):
                    for ent in manually_entities:
                        self.driver.add_entity(ent, manually_entities[ent])
                        print('manuelaly nodes')



        # Rekursiver Aufruf der Funktion
        self.start_extraction()


    # Die Funktion lädt den Datenbanktreiber für Neo4j
    def connect_db(self):
        self.driver = neo4jConnector()
