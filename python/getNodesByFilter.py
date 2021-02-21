from neo4j import GraphDatabase
import json

driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "test"), encrypted=False)

session = driver.session()


#API Endpoint Simulation
#filter = '{"types":{"0":{"ner":"CITY","text":"Berlin"}},"relationships":{}}'
filter = '{"types":[{"ner":"CITY","text":"Berlin"}],"relationships":[]}'

json_dict = json.loads(filter, encoding="utf-8")
#print(json_dict)
#print(type(json_dict))
filter_arr = json_dict

result_dict = []
msg_arr = {}

#types = filter_arr['types']
#print(types)
#first_element = types['0']
#print(first_element['ner'])
for types in filter_arr['types']:
#for key, value in filter_arr['types'].items():
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

    msg_arr['type'] = 'success'
    msg_arr['result'] = result_dict

    response = json.dumps(msg_arr, ensure_ascii=False).encode(encoding='utf-8')
    print(response)


'''
for types in filter_arr['types']:
    #print(types)


    ent_ner = "ent1.ner =~ '.*'"
    ent_text = "ent1.text =~ '.*'"
    # Ist der Typ gesetzt, so soll auch nach diesem gefiltert werden.
    if (types['ner'] != 'default'):
        ent_ner = "ent1.ner = '" + types['ner'] + "'"

    # Gleiches gilt für den Text der Entität.
    if (types['text'] != 'default'):
        ent_text = "ent1.text = '" + types['text'] + "'"

    query = "MATCH (rn1:RootNode)--(cf1:ContentField)--(sen1:Sentence)--(ent1:Entity) "
    query += "WHERE (" + ent_ner + " and " + ent_text + ") "
    query += "RETURN rn1.name as node_id, rn1.title as node_title, rn1.created as node_created, rn1.changed as node_changed, sen1.original_sent as sent, ent1.ner as ent_ner, ent1.text as ent_text "
    query += "ORDER BY rn1.changed DESC"

    #print(query)
    result = session.run(query)



    for record in result:
        result_dict.append(record)

    msg_arr['type'] = 'success'
    msg_arr['result'] = result_dict

    response = json.dumps(msg_arr, ensure_ascii=False).encode(encoding='utf-8')

    print(response)
'''