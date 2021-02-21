from neo4j import GraphDatabase
import json
import os

from builtins import str

class neo4jConnector(object):
    '''
    classdocs
    '''

    # Beim Initialisieren der Klasse werden aus der Konfigurationsdatei die Verbindungsdaten zu Neo4j geladen und versucht eine Verbindung aufzubauen.
    # Schlägt dies fehl wird eine Exception generiert.
    def __init__(self):
        '''
        Constructor
        '''


        try:
            # Database Credentials

            uri             = "bolt://neo4j:7687"

            userName        = "USER"

            password        = "PASSWORD"
            file_path = os.path.dirname(os.path.abspath(__file__))

            filename = os.path.join(file_path, 'config.json')

            file = open(filename, 'r', encoding="utf8")
            data = file.read()

            config = json.loads(data)
            #self._driver = GraphDatabase.driver(config['neo4j_url'], auth=(config['neo4j_user'], config['neo4j_password']), encrypted=False)
            self._driver = GraphDatabase.driver(uri, auth=(userName, password), encrypted=False)
            print("Connected...")
        except:
            raise

    def close(self):
        self._driver.close()

    # Die Funktion löscht alle Hauptknoten mit Content Fields, Sentences, Tags und Clauses aus der Datenbank. Da Entitäten und Synonyme nur ein einziges mal erzeugt
    # und danach immer nur mit Sentences oder Tags verknüpft werden, findet eine Löschung dieser nicht statt
    def del_node(self, node_id):
        with self._driver.session() as session:
            query = "MATCH (rn:RootNode)--(cf:ContentField)--(sen:Sentence)--(tag:Tag) "
            query += "WHERE (rn.name = '" + node_id + "') "
            query += "OPTIONAL MATCH (sen)--(clause:Clause) "
            query += "DETACH DELETE clause, tag, sen, cf, rn "

            result = session.run(query)

            return result

    # Die Funktion zählt alle Hauptknoten in der Datenbank und gibt die Anzahl zurück. Wird für die Anzeige im Drupal Backend benötigt, um die Anzahl der Noddes
    # in der Datenbank auszugeben
    def get_nodes_count(self, content_type):
        '''
        with self._driver.session() as session:
            query = "MATCH (rn:RootNode) "
            query += "WHERE (rn.content_type = '" + content_type + "') "
            query += "RETURN count(rn) as node_count"
        '''
        with self._driver.session() as session:
            query = "MATCH(n) RETURN count(n) AS node_count"
            result = session.run(query).data()

            return result

    # Diese Funktion speichert die zuvor per CoreNLP gewonnenen Informationen in der Datenbank ab.
    def create_root_node(self, extract_dict, node_id, content_type, content_field, title, created, changed):
        with self._driver.session() as session:

            # In Drupal gelöschte Entitäten werden wie manuell hinzugefügt in einer Datei geladen. Handelt es sich um Entitäten, die automatisch
            # von CoreNLP erzeugt und danach manuell gelöscht wurden, sollen bei einem erneuten Indexieren diese Entitäten nicht wieder hinzugefügt
            # und verknüpft werden. Daher wird hier die Datei eingelesen.
            removed_entities = None
            try:
                file = open('changed_entities.json', 'r', encoding="utf8")
                data = file.read()
                changed_entities = json.loads(data)
                removed_entities = changed_entities['removed_entities']
            except:
                pass

            # Sätze mit Clauses, NER (Named Entity Recognition und Relationen in seperaten Arrays speichern
            sent_clauses = extract_dict['sent_clauses']
            ner = extract_dict['entities']
            relations = extract_dict['relations']

            # Statt einem großen Query mit vielen Merges wird das Hinzufügen in Abschnitte eingeteilt. Ein großer Query mit vielen Merges brauch enorm viel Zeit.
            # Zunächst nur die Hauptknoten mit Content Field Knoten und deren Sentences erzeugen und miteinander verknüpfen.
            query = "MERGE (rn:RootNode {name:'" + str(node_id) + "', title: '" + title +"', content_type: '" + content_type + "', created: '" + created + "', changed:'" + changed + "'})"
            query += "MERGE (rn)-[:has_content_field]-(confield:ContentField {name:'" + content_field + "'})"

            for i in range(0, len(sent_clauses)):
                query += "MERGE (confield)-[:has_sentence]-(:Sentence {original_sent:'" + sent_clauses[i]["original_sent"] + "', shorten_lemma_original: '" + sent_clauses[i]["shorten_lemma_original"] + "'})"

            session.run(query)

            # Danach alle Clauses zu den Sentences hinzufügen und verknüpfen
            for i in range(0, len(sent_clauses)):

                sentence_query = "MERGE (:RootNode {name:'" + str(node_id) + "'})-[:has_content_field]-(:ContentField {name: '" + content_field + "'})-"
                sentence_query += "[:has_sentence]-(sen:Sentence {original_sent:'" + sent_clauses[i]["original_sent"] + "'})"
                query = sentence_query

                for key, value in sent_clauses[i]['clauses'].items():
                    query += "MERGE (sen)-[:has_clause]-(:Clause {original_clause:'" + value["original_clause"] + "', shorten_lemma_clause: '" + value["shorten_lemma_clause"] + "'}) "

                session.run(query)

                # Damit nicht jedes mal der komplette Query erneut geschrieben werden muss, wird ein Teil in der Variable abgespeichert.
                query = sentence_query

                # Alle Tags zu den Sentences hinzufügen und verknüpfen.
                for key, value in sent_clauses[i]['tags'].items():
                    query += "MERGE (sen)-[:has_tag]-(tag" + str(key) + ":Tag {label:'" + value["label"] + "'}) "

                session.run(query)

                # Zu den Tags die Synonyme hinzufügen und verknüpfen. Da Synonyme im Vergleich zu Tags, nur einmal in der Datenbank vorkommen sollen, wird zunächst mit einem Merge geschaut
                # ob das Synonym bereits vorhanden ist, andernfalls wird es durch Merge angelegt.
                for key, value in sent_clauses[i]['tags'].items():
                    if (len(value['synonyms'].items()) > 0):
                        query = sentence_query
                        query += "MERGE (sen)-[:has_tag]-(tag" + str(key) + ":Tag {label:'" + value["label"] + "'}) "
                        for key2, value2 in value['synonyms'].items():
                            query += "MERGE (syn" + str(key) + str(key2) + ":Synonym {label:'" + value2 + "'}) "
                            query += "MERGE (tag" + str(key) + ")-[:has_synonym]-(syn" + str(key) + str(key2) + ") "
                        session.run(query)

                query = sentence_query

                # Danach Entitäten hinzufügen. Für die Entitäten gilt das gleiche wie für die Synonyme.
                for key, value in ner[i].items():
                    if (removed_entities != None):
                        if (value['text'] not in removed_entities):
                            query += "MERGE (ent" + str(key) + ":Entity {text: '" + value['text'] + "'}) "
                            query += "ON CREATE SET ent" + str(key) + ".ner = '" + value['ner'] + "'"
                            query += "MERGE (sen)-[:has_entity]-(ent" + str(key) + ") "
                    else:
                        query += "MERGE (ent" + str(key) + ":Entity {text: '" + value['text'] + "'}) "
                        query += "ON CREATE SET ent" + str(key) + ".ner = '" + value['ner'] + "'"
                        query += "MERGE (sen)-[:has_entity]-(ent" + str(key) + ") "

                session.run(query)

                query = sentence_query

                # Wenn es Relationen zwischen den Entitäten gibt, werden diese hinzugefügt.
                for key, value in relations[i].items():
                    query += "MERGE (relent1" + str(key) + ":Entity {text: '" + value['subject'] + "'}) "
                    query += "ON CREATE SET relent1" + str(key) + ".ner = '" + value['subject_ner'] + "'"
                    query += "MERGE (relent2" + str(key) + ":Entity {text: '" + value['object'] + "'}) "
                    query += "ON CREATE SET relent2" + str(key) + ".ner = '" + value['object_ner'] + "'"
                    query += "MERGE (relent1" + str(key) + ")-[:" + value['relation'] + "]-(relent2" + str(key) + ") "


                result = session.run(query)

            return result

    # Die Funktion gibt alle Entitäten und Relationen in der Datenbank zurück. Wird für die Filtersuche, im speziellen für die Auswahlfelder beim Formular auf der Suchseite, benötigt
    # und für das Laden der Entitäten auf der Editierseite
    def get_entities(self):
        with self._driver.session() as session:
            '''
            query = "MATCH (ent:Entity) "
            query += "RETURN ent.ner as ner, ent.text as text"

            result = session.run(query).data()

            pronouns = ['he', 'she', 'it', 'we', 'they', 'theirs', 'ours', 'hers', 'his', 'its', 'her', 'his', 'their', 'our', 'him']
            entity_arr = {}

            entity_arr['types'] = {}
            entity_arr['relationships'] = []
            if (len(result) > 0):

                # Das Array soll so aufgebaut werden, dass für jeden Typ (NER) die Entitäten zugeordnet werden.
                for ent in result:
                    if (ent['ner'] not in entity_arr['types']):
                        entity_arr['types'][ent['ner']] = []

                    if (ent['text'].lower() not in pronouns):
                        add = True

                        # Doppelte Entitäten sollen nicht hinzugefügt werden.
                        for ner in entity_arr['types'][ent['ner']]:
                            if (ner.lower().replace('-', ' ') == ent['text'].lower().replace('-', ' ')):
                                add = False
                        if (add):
                            entity_arr['types'][ent['ner']].append(ent['text'])

            # Alle Relationen auslesen und dem Array hinzufügen.
            query = "MATCH (:Entity)-[rel]-(:Entity) "
            query += "RETURN collect(distinct Type(rel)) as rel"

            result = session.run(query).data()
            if (len(result) > 0):
                for rel in result[0]['rel']:
                    entity_arr['relationships'].append(rel)


            return entity_arr
            '''
            result = session.run("MATCH (ent: Entity) RETURN ent.ner as ner, ent.text as text")

            pronouns = ['he', 'she', 'it', 'we', 'they', 'theirs', 'ours', 'hers', 'his', 'its', 'her', 'his', 'their', 'our', 'him']
            entity_arr = {}
            entity_arr['types'] = {}
            entity_arr['relationships'] = []

            # Das Array soll so aufgebaut werden, dass für jeden Typ (NER) die Entitäten zugeordnet werden.
            for ent in result:
                #print(ent['ner'])
                if (ent['ner'] not in entity_arr['types']):
                    entity_arr['types'][ent['ner']] = []

                if (ent['text'].lower() not in pronouns):
                    add = True

                #print(ent['ner'])
                # Doppelte Entitäten sollen nicht hinzugefügt werden.
                for ner in ent['ner']:
                    if (ner.lower().replace('-', ' ') == ent['text'].lower().replace('-', ' ')):
                        add = False
                    if (add):
                        entity_arr['types'][ent['ner']].append(ent['text'])

            entity_types = list(dict.fromkeys(entity_arr['types'])) #TODO list durchiterieren und duplicate pro ET entfernen
            for entity_type in entity_types:
                #print(entity_type)
                entity_arr['types'][entity_type] = list(dict.fromkeys(entity_arr['types'][entity_type]))
            #print(entity_arr)
            # Alle Relationen auslesen und dem Array hinzufügen.
            query = "MATCH (:Entity)-[rel]-(:Entity) "
            query += "RETURN collect(distinct Type(rel)) as rel"

            result = session.run(query)

            if (result is not None):
                for record in result:
                    #print(record["rel"])
                    entity_arr['relationships'] = record["rel"]

            return entity_arr
    # Die Funktion gibt gefundene Hauptknoten der Nodes aus, die zu der Filtersuche passen
    def get_nodes_by_filter(self, filter_arr):
        with self._driver.session() as session:

            result_dict = []

            # Alle übermittelten Entitäten iterieren und den Suchquery zusammenbauen.
            for types in filter_arr['types']:
                #print(key)
                #print(value)
                #print(value['ner'])
                ent_ner = "ent1.ner =~ '.*'"
                ent_text = "ent1.text =~ '.*'"
                # Ist der Typ gesetzt, so soll auch nach diesem gefiltert werden.
                if (types['ner'] != 'default'):
                    ent_ner = "ent1.ner = '" + types['ner'] + "'"
                #Gleiches gilt fuer den Text
                if (types['text'] != 'default'):
                    ent_text = "ent1.text = '" + types['text'] + "'"

                query = "MATCH (rn1:RootNode)--(cf1:ContentField)--(sen1:Sentence)--(ent1:Entity) "
                query += "WHERE (" + ent_ner + " and " + ent_text + ") "
                query += "RETURN rn1.name as node_id, rn1.title as node_title, rn1.created as node_created, rn1.changed as node_changed, sen1.original_sent as sent, ent1.ner as ent_ner, ent1.text as ent_text "
                query += "ORDER BY rn1.changed DESC"
                #print(query)

                result = session.run(query)
                for record in result:
                    #print(record)
                    result_dict.append({'node_id': record['node_id'], 'node_title': record['node_title'], 'node_created' : record['node_created'], 'node_changed' : record['node_changed'], 'sent':record['sent'], 'ent_ner':record['ent_ner'], 'ent_text':record['ent_text']})

                    #print(result_dict)

            # Alle übermittelten Relationen iterieren und den Suchquery zusammenbauen.
            for relations in filter_arr['relationships']:

                # Der Suchquery wird analog zu dem Query bei den Entitäten aufgebaut, nur das hier zwei Entitäten und die Relation zwischen diesen betrachtet wird.
                ent1_ner = "ent1.ner =~ '.*'"
                ent2_ner = "ent2.ner =~ '.*'"
                ent1_text = "ent1.text =~ '.*'"
                ent2_text = "ent2.text =~ '.*'"
                rel = "Type(rel) =~ '.*'"
                if (relations['ner1'] != 'default'):
                    ent1_ner = "ent1.ner = '" + relations['ner1'] + "'"

                if (relations['ner2'] != 'default'):
                    ent2_ner = "ent2.ner = '" + relations['ner2'] + "'"

                if (relations['ner1_text'] != 'default'):
                    ent1_text = "ent1.text = '" + relations['ner1_text'] + "'"

                if (relations['ner2_text'] != 'default'):
                    ent2_text = "ent2.text = '" + relations['ner2_text'] + "'"

                if (relations['rel'] != 'default'):
                    rel = "Type(rel) = '" + relations['rel'] + "'"

                query = "MATCH (rn1:RootNode)--(cf1:ContentField)--(sen1:Sentence) "
                query += "MATCH (sen1)--(ent1:Entity) "
                query += "MATCH (sen1)--(ent2:Entity) "
                query += "MATCH (ent1)-[rel]-(ent2) "
                query += "WHERE (" + ent1_ner + " and " + ent1_text + " and " + ent2_ner + " and " + ent2_text + " and " + rel + ") "
                query += "RETURN rn1.name as node_id, rn1.title as node_title, rn1.created as node_created, rn1.changed as node_changed, sen1.original_sent as sent, ent1.ner as ent1_ner, ent1.text as ent1_text, ent2.ner as ent2_ner, ent2.text as ent2_text, Type(rel) as rel "
                query += "ORDER BY rn1.changed DESC"

                result = session.run(query)

                for record in result:
                    result_dict.append({'node_id': record['node_id'], 'node_title': record['node_title'], 'node_created' : record['node_created'], 'node_changed' : record['node_changed'], 'sent':record['sent'], 'ent1_ner':record['ent1_ner'], 'ent1_text':record['ent1_text'], 'ent2_ner':record['ent2_ner'], 'ent2_text':record['ent2_text'], 'rel':record['rel']})

                #if (len(result) > 0):
                #    for res in result:
                #        result_dict.append(res)

            return result_dict


    # Diese Funktion gibt anhand der IDs von Knoten Sentences und Clauses zurück. Wird beim Überprüfen von einem eingegeben Suchstring auf semantische Ähnlichkeit mit
    # Sentences und Clauses in der Datenbank benötigt. Im Suchindex stehen nur IDs von Knoten aus der Datenbank und Vektoren drin. Zu diesen IDs müssen die einzelnen Sentences
    # und Clauses geladen werden.
    def get_sent_clauses_by_id(self, id_list):
        with self._driver.session() as session:

            res_arr = {}
            res_arr['sentences'] = []
            res_arr['clauses'] = []
            query = "MATCH (rn:RootNode)--(cf:ContentField)--(sen:Sentence) "
            query += 'WHERE (ID(sen) in ' + str(id_list) + ') '
            query += "RETURN rn.name as node_id, rn.title as node_title, rn.created as node_created, rn.changed as node_changed, sen.original_sent as sent, sen.shorten_lemma_original as shorten_original"
            result = session.run(query).data()

            res_arr['sentences'] = result

            query = "MATCH (rn:RootNode)--(cf:ContentField)--(sen:Sentence)--(clause:Clause) "
            query += 'WHERE (ID(clause) in ' + str(id_list) + ') '
            query += "RETURN rn.name as node_id, rn.title as node_title, rn.created as node_created, rn.changed as node_changed, sen.original_sent as sent, clause.shorten_lemma_clause as shorten_clause"
            result = session.run(query).data()

            res_arr['clauses'] = result
            return res_arr

    # Diese Funktion gibt zu einem Suchquery bestehend aus einem Array mit Wörtern Hauptknoten mit ihren Sätze zurück, in denen die einzelnen Wörter als Tags oder Synonyme auftauchen.
    def get_tag_syn_for_sent(self, search_query):
        with self._driver.session() as session:

            # Der erste Query schaut, ob es Tags zu den Suchwörtern gibt und optional auch ob es Synonyme gibt, die den Suchwörtern entsprechen. Dieser Query liefert allerdings nur Ergebnisse zurück
            # wenn mindestens ein Tag mit einem Suchwort vorhanden ist, ansonsten schlägt dieser fehl. Der Query gibt nur Ergebnisse zurück wo die Anzahl von gefunden Tags oder Synonymen größer gleich
            # der Anzahl der Suchwörter ist.
            query = "MATCH (rn:RootNode)--(cf:ContentField)--(sen:Sentence) "
            query += "MATCH (sen)--(tag1:Tag) "
            query += "WHERE ("

            for i in range(0, len(search_query)):
                if (i == (len(search_query) - 1)):
                    query += "toLower(tag1.label) =~ toLower('.*" + search_query[i] + ".*')"
                else:
                    query += "toLower(tag1.label) =~ toLower('.*" + search_query[i] + ".*') or "

            query += ") "
            query += "OPTIONAL MATCH (sen)--(tag2:Tag)--(syn:Synonym) "
            query += "WHERE ("

            for i in range(0, len(search_query)):

                if (i == (len(search_query) - 1)):
                    query += "toLower(syn.label) =~ toLower('.*" + search_query[i] + ".*')"
                else:
                    query += "toLower(syn.label) =~ toLower('.*" + search_query[i] + ".*') or "

            query += ") "
            query += "WITH rn, sen, collect(DISTINCT tag1.label) as tags1, collect(DISTINCT tag2.label) as tags2, count(DISTINCT tag1) as tagCount, collect(DISTINCT syn) as syns, count(DISTINCT syn) as synCount "
            query += "WITH rn, sen, tags1, tags2, syns, sum(tagCount + synCount) as totalCount "
            query += "WHERE (totalCount >= " + str(len(search_query)) + ") "
            query += "RETURN rn.name as node_id, rn.title as node_title, rn.created as node_created, rn.changed as node_changed, sen.original_sent as sents "
            query += "LIMIT 100"
            #print(query)
            result = session.run(query).data()

            result_arr = []

            for res in result:
                exists = False
                i = 0
                # Hauptknoten sollen im result_arr nur einmal vorkommen und den Knoten werden dann die gefundenen Sätze zugeordnet.
                for i in range(0, len(result_arr)):
                    if (result_arr[i]['node_id'] == res['node_id']):
                        exists = True
                        break

                if (exists):

                    # Damit bei den Ergenissen auf der Suchseite nicht zu viele Sätze angezeigt werden, werden maximal drei Sätze einem Hauptknoten angezeigt.
                    if (len(result_arr[i]['sents']) <= 2):
                        result_arr[i]['sents'].append(res['sents'])
                else:
                    # Wenn der Hauptknoten noch nicht existiert, aus dem Satz ein Array machen, sodass bei der Überprüfung weiter oben diesem Array weitere Sätze hinzugefügt
                    # werden können.
                    elem = res
                    elem['sents'] = [elem['sents']]

                    result_arr.append(elem)

            # Da der obere Query fehl schlägt, wenn nicht mindestens ein Tag ein Suchwort beinhaltet, gibt es einen weiteren Query, der nur die Synonyme durchsucht.
            # Ablauf, Aufbau und Auswertung ist analog zu dem ersten Query.
            query = "MATCH (rn:RootNode)--(cf:ContentField)--(sen:Sentence) "
            query += "MATCH (sen)--(tag1:Tag)--(syn:Synonym) "
            query += "WHERE ("

            for i in range(0, len(search_query)):

                if (i == (len(search_query) - 1)):
                    query += "toLower(syn.label) =~ toLower('.*" + search_query[i] + ".*')"
                else:
                    query += "toLower(syn.label) =~ toLower('.*" + search_query[i] + ".*') or "

            query += ") "
            query += "WITH rn, sen, collect(DISTINCT tag1.label) as tags1, collect(DISTINCT syn) as syns, count(DISTINCT syn) as totalCount "
            query += "WITH rn, sen, tags1, syns, totalCount "
            query += "WHERE (totalCount >= " + str(len(search_query)) + ") "
            query += "RETURN rn.name as node_id, rn.title as node_title, rn.created as node_created, rn.changed as node_changed, sen.original_sent as sents "
            query += "LIMIT 100"

            result = session.run(query).data()

            for res in result:
                exists = False
                i = 0
                for i in range(0, len(result_arr)):
                    if (result_arr[i]['node_id'] == res['node_id']):
                        exists = True
                        break

                if (exists):
                    if (len(result_arr[i]['sents']) <= 2):
                        if(res['sents'] not in result_arr[i]['sents']):
                            result_arr[i]['sents'].append(res['sents'])
                else:
                    elem = res
                    elem['sents'] = [elem['sents']]
                    result_arr.append(elem)

            # Array nach dem Änderungsdatum sortieren
            result_arr = sorted(result_arr, key=lambda x: x['node_changed'], reverse=True)
            return result_arr

    # Diese Funktion wird verwendert, wenn die Funktion get_tag_syn_for_sent keine Ergebnisse liefert. Die Suche wird auf den Inhalt der gesamten Node
    # ausgeweitet und die Suchwörter müssen nicht alle in einem Satz stehen. Hier werden auch wieder zwei Suchquerys benötigt. Der Rest ist analog zu der
    # anderen Funktion.
    def get_tag_syn_for_node(self, search_query):
        with self._driver.session() as session:
            query = "MATCH (rn:RootNode) "
            query += "MATCH (rn)--(cf1:ContentField)--(sen1:Sentence)--(tag1:Tag) "
            query += "WHERE ("

            for i in range(0, len(search_query)):
                if (i == (len(search_query) - 1)):
                    query += "toLower(tag1.label) =~ toLower('.*" + search_query[i] + ".*')"
                else:
                    query += "toLower(tag1.label) =~ toLower('.*" + search_query[i] + ".*') or "

            query += ") "
            query += "OPTIONAL MATCH (rn)--(cf2:ContentField)--(sen2:Sentence)--(tag2:Tag)--(syn:Synonym) "
            query += "WHERE ("

            for i in range(0, len(search_query)):

                if (i == (len(search_query) - 1)):
                    query += "toLower(syn.label) =~ toLower('.*" + search_query[i] + ".*')"
                else:
                    query += "toLower(syn.label) =~ toLower('.*" + search_query[i] + ".*') or "

            query += ") "
            query += "WITH rn, collect(cf1) as cfs1, collect(cf2) as cfs2, collect(DISTINCT sen1.original_sent) as sents1, collect(DISTINCT sen2.original_sent) as sents2, collect(DISTINCT tag1) as tags1, collect(DISTINCT tag2) as tags2, count(DISTINCT tag1) as tagCount, collect(DISTINCT syn) as syns, count(DISTINCT syn) as synCount "
            query += "WITH rn, cfs1, cfs2, sents1, sents2, tags1, tags2, syns, sum(tagCount + synCount) as totalCount "
            query += "WHERE (totalCount >= " + str(len(search_query)) + ") "
            query += "RETURN rn.name as node_id, rn.title as node_title, rn.created as node_created, rn.changed as node_changed, sents1, sents2, totalCount "
            query += "ORDER BY rn.changed DESC"

            result = session.run(query).data()

            result_arr = []


            for res in result:
                exists = False
                i = 0
                for i in range(0, len(result_arr)):
                    if (result_arr[i]['node_id'] == res['node_id']):

                        exists = True
                        break

                if (exists):

                    # Bei diesem Suchquery werden zwei Arrays mit Sätzen zurückgegeben. Einmal mit Sätzen, bei denen die Suchwörter als Tags übereinstimmen und einmal bei denen
                    # die Suchwörter mit Synonyem übereinstimmen.
                    for sent in res['sents1']:
                        if (len(result_arr[i]['sents']) <= 2):
                            if(sent not in result_arr[i]['sents']):
                                result_arr[i]['sents'].append(sent)


                    for sent in res['sents2']:
                        if (len(result_arr[i]['sents']) <= 2):
                            if(sent not in result_arr[i]['sents']):
                                result_arr[i]['sents'].append(sent)
                else:
                    elem = res
                    elem['sents'] = []

                    for sent in elem['sents1']:
                        if (len(elem['sents']) <= 2):
                            if(sent not in elem['sents']):
                                elem['sents'].append(sent)


                    for sent in elem['sents2']:
                        if (len(elem['sents']) <= 2):
                            if(sent not in elem['sents']):
                                elem['sents'].append(sent)

                    del(elem['sents1'])
                    del(elem['sents2'])

                    result_arr.append(elem)

            query = "MATCH (rn:RootNode) "
            query += "MATCH (rn)--(cf:ContentField)--(sen:Sentence)--(tag:Tag)--(syn:Synonym) "
            query += "WHERE ("

            for i in range(0, len(search_query)):

                if (i == (len(search_query) - 1)):
                    query += "toLower(syn.label) =~ toLower('.*" + search_query[i] + ".*')"
                else:
                    query += "toLower(syn.label) =~ toLower('.*" + search_query[i] + ".*') or "

            query += ") "
            query += "WITH rn, collect(cf) as cfs, collect(DISTINCT sen.original_sent) as sents1, collect(DISTINCT tag) as tags, collect(DISTINCT syn) as syns, count(DISTINCT syn) as totalCount "
            query += "WITH rn, cfs, sents1, tags, syns, totalCount "
            query += "WHERE (totalCount >= " + str(len(search_query)) + ") "
            query += "RETURN rn.name as node_id, rn.title as node_title, rn.created as node_created, rn.changed as node_changed, sents1, totalCount "
            query += "ORDER BY rn.changed DESC"

            result = session.run(query).data()



            for res in result:
                exists = False
                i = 0
                for i in range(0, len(result_arr)):
                    if (result_arr[i]['node_id'] == res['node_id']):

                        exists = True
                        break

                if (exists):


                    for sent in res['sents1']:
                        if (len(result_arr[i]['sents']) <= 2):
                            if(sent not in result_arr[i]['sents']):
                                result_arr[i]['sents'].append(sent)

                else:
                    elem = res
                    elem['sents'] = []

                    for sent in elem['sents1']:
                        if (len(elem['sents']) <= 2):
                            if(sent not in elem['sents']):
                                elem['sents'].append(sent)

                    del(elem['sents1'])

                    result_arr.append(elem)



            result_arr = sorted(result_arr, key=lambda x: x['node_changed'], reverse=True)
            return result_arr

    # Diese Funktion liefert zu einer Node ID von einer Drupal Node alle dazugehörigen Entitäten aus. Wird für die Graphenanzeige bei der Ansicht der Node benötigt
    def get_entities_by_id(self, node_id):
        with self._driver.session() as session:

            query = "MATCH (rn:RootNode)--(cf:ContentField)--(sen:Sentence)--(ent:Entity) "
            query += "WHERE (rn.name = '" + str(node_id) + "') "
            query += "RETURN DISTINCT rn.name as node_id, ent.ner as ent_ner, ent.text as ent_text "
            query += "ORDER BY ent.ner ASC"

            result = session.run(query)

            res_dict = []
            for record in result:
                res_dict.append({'node_id': record['node_id'], 'ent_ner': record['ent_ner'], 'ent_text': record['ent_text']})

            return res_dict



    # Diese Funktion liefert zu einer Node ID von einer Drupal Node alle Entitäten aus, die durch einen Relation miteinander verbunden sind. Da nicht alle Entitäten
    # zwingend mit anderen Entitäten verbunden sein müssen, existieren zwei getrennte Funktionen.
    def get_relations_by_id(self, node_id):
        with self._driver.session() as session:

            query = "MATCH (rn:RootNode) "
            query += "MATCH (rn)--(cf:ContentField)--(sen:Sentence)--(ent:Entity) "
            query += "MATCH (rn)--(cf2:ContentField)--(sen2:Sentence)--(ent2:Entity) "
            query += "MATCH (ent)-[rel]-(ent2)"
            query += "WHERE (rn.name = '" + str(node_id) + "') "
            query += "RETURN DISTINCT rn.name as node_id, ent.ner as ent_ner, ent.text as ent_text, ent2.ner as ent2_ner, ent2.text as ent2_text, Type(rel) as rel "

            result = session.run(query)
            res_dict = []
            for record in result:
                res_dict.append({'node_id': record['node_id'], 'ent_ner': record['ent_ner'], 'ent_text': record['ent_text'], 'ent2_ner': record['ent2_ner'], 'ent2_text': record['ent2_text'], 'rel': record['rel']})

            return res_dict

    # Diese Funktion arbeitet ähnlich wie get_node_by_id, nur das im Mittelpunkt eine Entität steht und keine Drupal Node ID. Wenn beim Grapen in der Ansicht der Node
    # doppelt auf eine Entität geklickt wird, sollen alle Entitäten und Hauptknoten geladen werden, die mit dieser Entität in Verbindung stehen. Diese Funktion lädt alle
    # in Verbindung mit der Entität stehenden Hauptknoten.
    def get_node_by_entity(self, ent_text, ent_ner):
        with self._driver.session() as session:
            query = "MATCH (rn:RootNode)--(cf:ContentField)--(sen:Sentence)--(ent:Entity) "
            query += "WHERE (ent.text = '" + ent_text + "' and ent.ner = '" + ent_ner + "') "
            query += "RETURN DISTINCT rn.name as node_id, rn.title as node_title "

            result = session.run(query).data()

            return result

    # Siehe get_node_by_entity. Hier werden die anderen Entitäten geladen, die mit einer Entität in Verbindung stehen.
    def get_entities_relations_by_entity(self, ent_text, ent_ner):
        with self._driver.session() as session:
            query = "MATCH (ent:Entity)-[rel]-(ent2:Entity) "
            query += "WHERE (ent.text = '" + ent_text + "' and ent.ner = '" + ent_ner + "') "
            query += "RETURN DISTINCT ent.text as ent_text, ent.ner as ent_ner, ent2.text as ent2_text, ent2.ner as ent2_ner, Type(rel) as rel  "

            result = session.run(query).data()

            return result

    # Die in get_entities_relations_by_entity geladenen Entitäten können untereinander ebenfalls in Beziehung zueinander stehen. Diese Funktion lädt diese Relationen.
    def get_additional_relations(self, ent_list):
        with self._driver.session() as session:
            query = "MATCH (ent:Entity)-[rel]-(ent2:Entity) "
            query += "WHERE (ent.text in " + str(ent_list) + " and ent2.text in " + str(ent_list) + ") "
            query += "RETURN DISTINCT ent.text as ent_text, ent.ner as ent_ner, ent2.text as ent2_text, ent2.ner as ent2_ner, Type(rel) as rel  "

            result = session.run(query).data()

            return result


    # Bei der Ansicht der Node können Entitäten editiert werden und zum Löschen markiert werden. Diese Funktion löscht, bzw. editiert die geänderten Entitäten in der Datenbank.
    def change_entities(self, entities):
        with self._driver.session() as session:

            for ent in entities.values():
                if (ent['delete'] == 1):
                    query = "MATCH (sen:Sentence)--(ent:Entity) "
                    query += "WHERE (ent.text = '" + ent['text'] + "') "
                    query += "DETACH DELETE ent "
                    query += "RETURN sen"

                    result = session.run(query).data()
                else:
                    query = "MATCH (ent:Entity) "
                    query += "WHERE (ent.text = '" + ent['text'] + "') "
                    query += "SET ent.ner = '" + ent['ner'] + "'"
                    query += "RETURN ent "
                    query += "ORDER BY ent.ner ASC"

                    result = session.run(query).data()

    # Beim manuellen Hinzufügen von Entitäten, wird vorher überprüft, ob diese bereits in der Datenbank vorhanden ist.
    def check_entity_exists(self, entity):
        with self._driver.session() as session:

            query = "MATCH (ent:Entity) "
            query += "WHERE (toLower(ent.text) = toLower('" + str(entity) + "')) "
            query += "RETURN ent.text"

            result = session.run(query).data()

            return result

    # Existiert die Entität noch nicht in der Datenbank, so wird diese hinzugefügt.
    def add_entity(self, entity_text, entity_ner):
        with self._driver.session() as session:

            # Es wird überprüft, ob es Hauptknoten mit Sätzen gibt, die den eingegebenen Text der Entität beinhalten. Andernfalls ist das Hinzufügen sinnfrei.
            query = "MATCH (rn:RootNode)--(:ContentField)--(sen:Sentence) "
            query += "WHERE (toLower(sen.original_sent) =~ toLower('.*" + entity_text + ".*')) "
            query += "RETURN sen.original_sent as sent "

            result = session.run(query).data()

            if (len(result) > 0):
                # Existieren Sätze, die diese Entität beinhalten, wird die Entität erst einmal erstellt und anschließend mit den Sätzen verknüpft. So muss nicht eine Entität
                # manuell zu x Nodes hinzugefügt werden.
                query = "MERGE (ent:Entity {text: '" + entity_text + "', ner: '" + entity_ner + "'}) "
                query += "WITH ent "
                query += "MATCH (rn:RootNode)--(:ContentField)--(sen:Sentence) "
                query += "WHERE (toLower(sen.original_sent) =~ toLower('.*" + entity_text + ".*')) "
                query += "WITH ent, rn, sen "
                query += "MERGE (sen)-[:has_entity]-(ent) "
                query += "RETURN DISTINCT rn.name as node_id, rn.title as node_title, ent.text as ent_text, ent.ner as ent_ner "

                result = session.run(query).data()


            return result


