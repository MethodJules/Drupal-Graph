<?php
/**
 * Created by PhpStorm.
 * User: Corin
 * Date: 03.06.2019
 * Time: 21:01
 */

namespace Drupal\nlp_search\Controller;

use Drupal\Core\Controller\ControllerBase;

/**
 * Defines HelloController class.
 */
class GraphController extends ControllerBase {


    //Wird bei einer Node im Graphen auf eine Entiät geklickt, wird diese Funktion aufgerufen. Diese holt die Hauptknoten
    //und verbundene Entitäten zu der ausgewählten Entität aus der Datenbank und über gibt die Informationen an das
    //Javascript vis_load.js
    public function content($ent_text, $ent_ner) {

        $ent_text = urldecode($ent_text);
        $ent_ner = urldecode($ent_ner);

        $content = array();
        if (!empty($ent_text) && !empty($ent_ner)) {

            $config = \Drupal::config('nlp_search.settings');
            $saved_python_flask_url = $config->get('nlp_search_basic_python_flask_url');

            if (!empty($saved_python_flask_url)) {
                if ($saved_python_flask_url[strlen($saved_python_flask_url) - 1] != '/') {
                    $saved_python_flask_url .= '/';
                }

                //cUrl Aufruf an die Python Flask Anwendung, die die Hauptknoten, Entitäten und Relationen zurückliefert.
                $ch = curl_init();

                curl_setopt($ch, CURLOPT_URL, $saved_python_flask_url . "get-entities-relations-by-entity");
                curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
                curl_setopt($ch, CURLOPT_TIMEOUT, 10);
                curl_setopt($ch, CURLOPT_POST, 1);
                curl_setopt($ch, CURLOPT_POSTFIELDS,
                    http_build_query(array('ent_text' => $ent_text, 'ent_ner' => $ent_ner)));

                curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

                $response = curl_exec($ch);

                if ($response === FALSE) {
                    \Drupal::messenger()->addMessage(curl_error($ch), 'error');
                } else {

                    $response = json_decode($response, true);

                    if ($response['type'] == 'success') {
                        if (count($response['result']['root_nodes']) > 0) {
                            $content[] = [
                                '#markup' => '<p>' . t('Results for @ent_text (@ent_ner)', ['@ent_text' => $ent_text, '@ent_ner' => $ent_ner]) . '</p>'
                            ];

                            //Die ausgewählte Entität als erstes dem Entitäten-Array hinzufügen.
                            $label = $ent_text;

                            //Label wird innerhalb des Knotens im Graphen angezeigt und damit dieser Knoten nicht zu groß
                            //wird, findet eine Kürzung statt. Per Tooltip und dem Attribut title wird der gesamte Text
                            //angezeigt.
                            if (strlen($label) > 10) {
                                $label = substr($label, 0, 10) . '...';

                            }

                            $entities = array();
                            $relations = array();

                            $added_entities = array();

                            $entities[] = [
                                'id' => 1,
                                'title' => $ent_text . '<br>' . $ent_ner,
                                'label' => $label,
                                'color' => '#cfccaf',
                                'ent_ner' => $ent_ner,
                                'ent_text' => $ent_text,
                            ];

                            $added_entities[$ent_text] = 1;

                            $counter = 2;

                            //Aus dem Ergebnis alle Hauptknoten iterieren, dem Entitäten-Array hinzufügen, den Counter erhöhen
                            //und die IDs dem Relationen-Array hinzufügen.
                            foreach ($response['result']['root_nodes'] as $resp) {

                                $label = $resp['node_title'];

                                if (strlen($label) > 10) {
                                    $label = mb_substr ( $label, 0, 10, 'UTF-8') . '...';

                                }
                                $entities[] = [
                                    'id' => $counter,
                                    'title' => $resp['node_title'] . '<br>Root Node',
                                    'label' => $label,
                                    'color' => '#537295',
                                    'ent_text' => $resp['node_title'],
                                    'ent_ner' => 'root_node',
                                    'drupal_id' => $resp['node_id']
                                ];

                                $relations[] = [
                                    'from' => 1,
                                    'to' => $counter,
                                    //'label' => 'has_entity',
                                ];
                                $counter++;
                            }

                            //Alle Entitäten, die in Verbindung mit der ausgewählten Entität stehen iterieren, dem Entitäten-
                            //Array hinzufügen, den Counter erhöhen und die IDs dem Relationen-Array hinzufügen.
                            $counter = count($entities) + 1;
                            foreach ($response['result']['entities_relations'] as $resp) {

                                $ent_id = 0;

                                if (isset($added_entities[$resp['ent2_text']])) {
                                    $relations[] = [
                                        'from' => 1,
                                        'to' => $added_entities[$resp['ent2_text']],
                                        'label' => $resp['rel'],
                                    ];
                                } else {
                                    $label = $resp['ent2_text'];

                                    if (strlen($label) > 10) {
                                        $label = mb_substr ( $label, 0, 10, 'UTF-8') . '...';
                                    }
                                    $entities[] = [
                                        'id' => $counter,
                                        'title' => $resp['ent2_text'] . '<br>' . $resp['ent2_ner'],
                                        'label' => $label,
                                        'color' => '#cfccaf',
                                        'ent_text' => $resp['ent2_text'],
                                        'ent_ner' => $resp['ent2_ner'],
                                    ];

                                    $relations[] = [
                                        'from' => 1,
                                        'to' => $counter,
                                        'label' => $resp['rel'],
                                    ];

                                    $added_entities[$resp['ent2_text']] = $counter;
                                    $counter++;
                                }
                            }


                            //Anschließend die Relationen zwischen den Entitäten iterieren und diese dem Relationen-
                            //Array hinzufügen.
                            $added_relations = array();
                            foreach ($response['result']['additional_relations'] as $resp) {

                                $rel_exist = false;

                                foreach ($added_relations[$resp['rel']] as $add_rel) {
                                    if (in_array($resp['ent_text'], $add_rel) && in_array($resp['ent2_text'], $add_rel)) {
                                        $rel_exist = true;
                                        break;
                                    }
                                }

                                if (!$rel_exist) {
                                    $relations[] = [
                                        'from' => $added_entities[$resp['ent_text']],
                                        'to' => $added_entities[$resp['ent2_text']],
                                        'label' => $resp['rel']
                                    ];

                                    $added_relations[$resp['rel']][] = [$resp['ent_text'], $resp['ent2_text']];
                                }
                            }

                            $content['network_graph'] = array(
                                '#markup' => '<div id="nlp-network-graph"></div>',
                            );

                            //Definieren welche Dateien geladen werden sollen (css und js) und als drupalSettings die Arrays
                            //für Entitäten und Relationen übergeben. Diese können im Javascript verwendet werden.
                            $content['#attached']['library'][] = 'nlp_search/nlpsearch_vis';
                            $content['#attached']['drupalSettings']['nlp_search']['entities'] = $entities;
                            $content['#attached']['drupalSettings']['nlp_search']['relations'] = $relations;

                        } else {
                            $content[] = [
                                '#markup' => '<p>' . t('No results') . '</p>'
                            ];
                        }
                    } else {
                        \Drupal::messenger()->addMessage($response['result'], 'error');
                    }
                }

                curl_close($ch);

            } else {
                \Drupal::messenger()->addMessage(t('Missing configuration python flask url'), 'error');
            }
        } else {
            \Drupal::messenger()->addMessage(t('Nothing to search for'), 'error');
        }

        return $content;
    }

}