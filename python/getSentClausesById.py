from neo4j import GraphDatabase
import json

driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "test"), encrypted=False)

session = driver.session()

similar_ids = [290, 11, 16]

res_arr = {}
res_arr['sentences'] = []
res_arr['clauses'] = []

id_list = similar_ids
query = "MATCH (rn:RootNode)--(cf:ContentField)--(sen:Sentence) "
query += 'WHERE (ID(sen) in ' + str(id_list) + ') '
query += "RETURN rn.name as node_id, rn.title as node_title, rn.created as node_created, rn.changed as node_changed, sen.original_sent as sent, sen.shorten_lemma_original as shorten_original"

result = session.run(query)


for record in result:
    res_arr['sentences'].append({'node_id' : record['node_id'], 'node_title' : record['node_title'], 'node_created' : record['node_created'], 'node_changed': record['node_changed'], 'sent' : record['sent'], 'shorten_original' : record['shorten_original']})
#print(res_arr['sentences'])

query = "MATCH (rn:RootNode)--(cf:ContentField)--(sen:Sentence)--(clause:Clause) "
query += 'WHERE (ID(clause) in ' + str(id_list) + ') '
query += "RETURN rn.name as node_id, rn.title as node_title, rn.created as node_created, rn.changed as node_changed, sen.original_sent as sent, clause.shorten_lemma_clause as shorten_clause"
result = session.run(query)

for record in result:
    res_arr['clauses'].append({'node_id' : record['node_id'], 'node_title' : record['node_title'], 'node_created' : record['node_created'], 'node_changed': record['node_changed'], 'sent' : record['sent'], 'shorten_original' : record['shorten_clause']})

print(res_arr)