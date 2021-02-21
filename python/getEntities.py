from neo4j import GraphDatabase

def get_entities():

    driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "test"), encrypted=False)

    session = driver.session()

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
    #ner = [record["ner"] for record in result]
    #ner = []
    #text = []
    #for record in result:
    #    ner.append(record["ner"])
    #    text.append(record["text"])

    #print(ner)
    #print(text)
    #print(result.keys())