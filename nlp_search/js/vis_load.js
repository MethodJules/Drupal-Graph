
(function ($) {
    $(document).ready(function () {

        //Entitäten und Relationen vom PHP Script auslesen.
        var entities = drupalSettings.nlp_search.entities;
        var relations = drupalSettings.nlp_search.relations;

        console.log(drupalSettings.nlp_search);

        //Knoten und Kanten für Vis setzen.
        var nodes = new vis.DataSet(entities);
        var edges = new vis.DataSet(relations);

        // create a network
        var container = document.getElementById('nlp-network-graph');
        var data = {
            nodes: nodes,
            edges: edges
        };
        var options = {
            autoResize: true,
            interaction: {
                //Navigationsbuttons aktivieren
                navigationButtons: true,
            },
            layout: {
                //Hier wurde irgendein Wert genommen, damit der Graph immer gleich gerendert wird.
                randomSeed: 976020
            },

            nodes: {
                shape: 'circle',
                size: 30,
                font: {
                    size: 14,
                    color: '#000'
                },
                borderWidth: 2
            },
            edges: {
                width: 2,
                smooth: {
                    type: 'dynamic'
                }
            },

            physics: {
                //Die Physics Engine hat sich nach ein bisschen rumprobieren als beste Engine für das Anzeigen von den
                //Knoten herausgestellt. Es wird etwas mehr Platz zwischen den Knoten gelassen, was bei anderen Engines
                //nicht unbedingt der Fall war.
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {
                    avoidOverlap: 0
                }
            }

        };

        //Graph erzeugen und rendern lassen.
        network = new vis.Network(container, data, options);


        //Bei Doppelklick auf einen Knoten entweder zu einer Node gehen oder falls eine Entität ausgewählt wurde, die
        //Entität per Parameter an den entsprechenden Controller weiter geben, der einen anderen Grapen ausgehend von
        //der Entität rendert.
        network.on('doubleClick', function(properties) {
            if (properties.nodes.length > 0) {
                var node_id = properties.nodes[0];

                var url = '';
                if (nodes.get(node_id).ent_ner === 'root_node') {
                    url = drupalSettings.path.baseUrl + 'node/' + nodes.get(node_id).drupal_id;
                } else {
                    url = drupalSettings.path.baseUrl + 'nlp-search/graph-view/' + encodeURI(nodes.get(node_id).ent_text) + '/' + encodeURI(nodes.get(node_id).ent_ner);
                }

                window.location.href = url;
            }

        });
    });
})(jQuery);