from neo4j import GraphDatabase
import json

driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "test"), encrypted=False)

session = driver.session()

node_id = 1835

query = "MATCH (rn:RootNode)--(cf:ContentField)--(sen:Sentence)--(ent:Entity) "
query += "WHERE (rn.name = '" + str(node_id) + "') "
query += "RETURN DISTINCT rn.name as node_id, ent.ner as ent_ner, ent.text as ent_text "
query += "ORDER BY ent.ner ASC"

result = session.run(query)

res_dict = []
for record in result:
    res_dict.append({'node_id': record['node_id'], 'ent_ner': record['ent_ner'], 'ent_text': record['ent_text']})



print(res_dict)