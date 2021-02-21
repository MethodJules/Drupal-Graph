from neo4j import GraphDatabase
import json

driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "test"), encrypted=False)
session = driver.session()
search_query = "who immigrated to palestine and promoting social work"
# Der erste Query schaut, ob es Tags zu den Suchwörtern gibt und optional auch ob es Synonyme gibt, die den Suchwörtern entsprechen. Dieser Query liefert allerdings nur Ergebnisse zurück
# wenn mindestens ein Tag mit einem Suchwort vorhanden ist, ansonsten schlägt dieser fehl. Der Query gibt nur Ergebnisse zurück wo die Anzahl von gefunden Tags oder Synonymen größer gleich
# der Anzahl der Suchwörter ist.
query = "MATCH (rn:RootNode)--(cf:ContentField)--(sen:Sentence) "
query += "MATCH (sen)--(tag1:Tag) "
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
        print(query)
        result = session.run(query) #TODO Aendern

        result_arr = []

        print(len(result_arr))

        for record in result:
            #print(record['node_id'])
            #print(record['sents'])
            exists = False
            i = 0
            # Hauptknoten sollen nur im result_arr nur einmal vorkommen und den Knoten werden dann die gefundenen Sätze zugeordnet
            for i in range(0, len(result_arr)):
                print(i)
                if(result_arr[i]['node_id'] == record['node_id']):
                    print('zeile 48')
                    exists = True
                    break
                if (exists):
                    #Damit bei den Ergebnissen auf der Suchseite nicht zu viele Saetze angezeigt werden, werden maximal drei Saetze vom Hauptknoten angezeigt
                    if(len(result_arr[i]['sents']) <= 2):
                        result_arr[i]['sents'].append([record['sents']])
                else:
                    #Wenn der Hauptknoten noch nicht existiert, aus dem Satz ein Array machen, sodass bei der Ueberpruefung weiter oben
                    # diesem Array weiter Saetze hinzugefuegt werden koennen
                    print('Hauptknoten existiert noch nicht...')
                    elem = record
                    elem['sents'] = [elem['sents']]

                    result_arr.append(elem)
print(result_arr)



'''
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

result = session.run(query)
'''
'''
for record in result:
    print(record)
'''
'''
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
                '''
