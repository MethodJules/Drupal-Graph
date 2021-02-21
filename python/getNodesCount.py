from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "test"), encrypted=False)

session = driver.session()

query = "MATCH(n) RETURN count(n) AS node_count"
result = session.run(query)

for record in result:
    print(record["node_count"])