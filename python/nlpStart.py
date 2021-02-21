# coding=latin-1
from nlpProcessClass import nlpProcess
from neo4j import GraphDatabase
import time
print('Warte.........................')
time.sleep(1)
print('Weiter........................')


#------------------------
# Wird vom Cronjob ausgeführt und instanziiert die Klasse nlpProcess
nlpProc = nlpProcess()
tries = 3

# 3 Versuche für den Verbindungsaufbau zur Datenbank, ansonsten wird die gesamte Aufgabe abgebrochen
for i in range(tries):

    try:
        nlpProc.connect_db()
        nlpProc.add_log("Starting NLP Task")
        nlpProc.start_extraction()
    except Exception as e:

        if (type(e).__name__ == "ServiceUnavailable" and i < tries - 1):
            nlpProc.add_log(str(e))
            nlpProc.add_log("Retry connecting")
            continue
        else:
            raise


    break




'''
#------------------------

# Wird vom Cronjob ausgeführt und instanziiert die Klasse nlpProcess
#nlpProc = nlpProcess()
#tries = 3

# Database Credentials

uri             = "bolt://neo4j:7687"

userName        = "neo4j"

password        = "test"



# Connect to the neo4j database server

graphDB_Driver  = GraphDatabase.driver(uri, auth=(userName, password), encrypted=False)



# CQL to query all the universities present in the graph

cqlNodeQuery          = "MATCH (x:university) RETURN x"



# CQL to query the distances from Yale to some of the other Ivy League universities

cqlEdgeQuery          = "MATCH (x:university {name:'Yale University'})-[r]->(y:university) RETURN y.name,r.miles"



# CQL to create a graph containing some of the Ivy League universities

cqlCreate = """CREATE (cornell:university { name: "Cornell University"}),

(yale:university { name: "Yale University"}),

(princeton:university { name: "Princeton University"}),

(harvard:university { name: "Harvard University"}),



(cornell)-[:connects_in {miles: 259}]->(yale),

(cornell)-[:connects_in {miles: 210}]->(princeton),

(cornell)-[:connects_in {miles: 327}]->(harvard),



(yale)-[:connects_in {miles: 259}]->(cornell),

(yale)-[:connects_in {miles: 133}]->(princeton),

(yale)-[:connects_in {miles: 133}]->(harvard),



(harvard)-[:connects_in {miles: 327}]->(cornell),

(harvard)-[:connects_in {miles: 133}]->(yale),

(harvard)-[:connects_in {miles: 260}]->(princeton),



(princeton)-[:connects_in {miles: 210}]->(cornell),

(princeton)-[:connects_in {miles: 133}]->(yale),

(princeton)-[:connects_in {miles: 260}]->(harvard)"""



# Execute the CQL query

with graphDB_Driver.session() as graphDB_Session:

    # Create nodes

    graphDB_Session.run(cqlCreate)



    # Query the graph

    nodes = graphDB_Session.run(cqlNodeQuery)



    print("List of Ivy League universities present in the graph:")

    for node in nodes:

        print(node)



    # Query the relationships present in the graph

    nodes = graphDB_Session.run(cqlEdgeQuery)



    print("Distance from Yale University to the other Ivy League universities present in the graph:")

    for node in nodes:

        print(node)

'''
'''
# 3 Versuche für den Verbindungsaufbau zur Datenbank, ansonsten wird die gesamte Aufgabe abgebrochen
for i in range(tries):

    try:
        nlpProc.connect_db()
        nlpProc.add_log("Starting NLP Task")
        print("Starting NLP Task")
        nlpProc.start_extraction()
    except Exception as e:

        if (type(e).__name__ == "ServiceUnavailable" and i < tries - 1):
            nlpProc.add_log(str(e))
            nlpProc.add_log("Retry connecting")
            continue
        else:
            raise


    break
'''