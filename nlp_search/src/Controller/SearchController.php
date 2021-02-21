<?php
/**
 * Created by PhpStorm.
 * User: Corin
 * Date: 25.04.2019
 * Time: 17:31
 */

namespace Drupal\nlp_search\Controller;

use Drupal\Core\Controller\ControllerBase;

class SearchController extends ControllerBase {

    //Diese Funktion bekommt die in der SearchForm definierten Filter übergeben, holt die Informationen von der Python
    //Flask Anwendung und stellt das Ergebnis in Form einer Liste mit ggf. mehreren Seiten zur Verfügung.
    public function filter($search_content) {

        //Die Filter werden als Parameter an die URL gehängt und sind kodiert.
        $nlp_filter = urldecode($search_content);
        $nlp_filter = json_decode($nlp_filter, true);

        $content = array();
        if (!$nlp_filter) {
            \Drupal::messenger()->addMessage(t('Invalid parameters'), 'error');
        } else {
            if (count($nlp_filter['types']) > 0 || count($nlp_filter['relationships']) > 0) {

                $config = \Drupal::config('nlp_search.settings');
                $saved_python_flask_url = $config->get('nlp_search_basic_python_flask_url');

                if (!empty($saved_python_flask_url)) {
                    if ($saved_python_flask_url[strlen($saved_python_flask_url) - 1] != '/') {
                        $saved_python_flask_url .= '/';
                    }

                    //cUrl Aufruf und holen der Suchergebnisse von der Python Flask Anwendung.
                    $ch = curl_init();

                    curl_setopt($ch, CURLOPT_URL, $saved_python_flask_url . "get-nodes-by-filter");
                    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
                    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
                    curl_setopt($ch, CURLOPT_POST, 1);
                    curl_setopt($ch, CURLOPT_POSTFIELDS,
                        http_build_query(array('filter' => json_encode($nlp_filter))));

                    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

                    $response = curl_exec($ch);

                    if ($response === FALSE) {
                        \Drupal::messenger()->addMessage(curl_error($ch), 'error');
                    } else {

                        $result_arr = json_decode($response, true);

                        if ($result_arr['type'] == 'success') {

                            if (count($result_arr['result']) == 0) {
                                $content[] = [
                                    '#markup' => '<p>' . t('No search results') . '</p>'
                                ];
                            } else {

                                $number_results = '<h3>' . t('@number results', ['@number' => count($result_arr['result'])]) . '</h3>';

                                $content[] = [
                                    '#markup' => '<div class="nlp-search-results">' . $number_results
                                ];

                                //Seite definieren, bzw. aus Parameter laden, wenn dieser vorhanden ist. Ebenfalls wird
                                //definiert wie viele Einträge pro Seite angezeigt werden sollen.
                                $page = 0;
                                $num_per_page = 10;
                                if (isset($_GET['page'])) {
                                    $page = $_GET['page'];
                                }

                                //Es werden immer alle Suchergebnisse aus der Datenbank geladen. Wenn durch die Seiten navigiert
                                //wird, sind immer unterschiedliche Einträge notwendig. Hier wird definiert wo im Array bei der Iteration
                                //begonnen und wo gestoppt werden soll.
                                $start = $num_per_page * $page;
                                $end = $start + $num_per_page;

                                //Der Page ist im Drupal Core enthalten und wird intialisiert.
                                pager_default_initialize(count($result_arr['result']), $num_per_page);

                                global $base_url;

                                //Von vorher definierten Start bis zum Ende für die aktuelle Seite das Array aus der
                                //Datenbank iterieren und die HTML-Struktur zusammenbauen.
                                for ($start; $start < $end; $start++) {

                                    if ($start >= count($result_arr['result'])) {
                                        break;
                                    }
                                    $html = '<li>';
                                    $html .= '<h3 class="nlp-search-result-title">';
                                    $html .= '<a href="' . $base_url . '/node/' . $result_arr['result'][$start]['node_id'] . '">' . $result_arr['result'][$start]['node_title'] . '</a>';
                                    $html .= '</h3>';
                                    $html .= '<div class="nlp-search-result-snippet-info">';
                                    $html .= '<p class="nlp-search-result-snippet">';
                                    $html .= '<span>';
                                    $html .= '<b>' . t('Changed') . '</b>: ' . date("Y-m-d H:i:s", $result_arr['result'][$start]['node_changed']) . ' | <b>' . t('Created') . '</b>: ' . date("Y-m-d H:i:s", $result_arr['result'][$start]['node_created']);
                                    $html .= '</span>';
                                    $html .= '<span>';

                                    //Wurden Filter mit Relationen definiert und entsprechende Ergebnisse sind zurückgekommen
                                    //werden an dieser Stelle die Ergebnisse ebenfalls dargestellt.
                                    if (isset($result_arr['result'][$start]['rel'])) {
                                        $html .= '<b>' . t('Entity') . '</b>: ' . $result_arr['result'][$start]['ent1_text'] . ' (' . $result_arr['result'][$start]['ent1_ner'] . ')' . ' | ';
                                        $html .= '<b>' . t('Relation') . '</b>: ' . $result_arr['result'][$start]['rel'] . ' | ';
                                        $html .= '<b>' . t('Entity') . '</b>: ' . $result_arr['result'][$start]['ent2_text'] . ' (' . $result_arr['result'][$start]['ent2_ner'] . ')';
                                    } else {
                                        $html .= '<b>' . t('Entity') . '</b>: ' . $result_arr['result'][$start]['ent_text'] . ' (' . $result_arr['result'][$start]['ent_ner'] . ')';
                                    }
                                    $html .= '</span>';
                                    $html .= '<span>';
                                    $html .= $result_arr['result'][$start]['sent'];
                                    $html .= '</span>';
                                    $html .= '</p>';
                                    $html .= '</div>';
                                    $html .= '</li>';

                                    $content[] = [
                                        '#markup' => $html,

                                    ];


                                }
                                $content[] = [
                                    '#markup' => '</div>'
                                ];

                                $content[] = ['#type' => 'pager'];
                                $content['#attached']['library'][] = 'nlp_search/nlpsearch_basic';

                            }
                        } else {
                            \Drupal::messenger()->addMessage($result_arr['result'], 'error');
                        }
                    }

                    curl_close($ch);
                } else {
                    \Drupal::messenger()->addMessage(t('Missing configuration python flask url'), 'error');
                }

            } else {
                \Drupal::messenger()->addMessage(t('Nothing to search for'), 'error');
            }
        }

        return $content;
    }

    //Die Funktion wird aufgerufen, wenn bei der SearchForm eine Volltextsuche gestartet wird.
    public function fulltext($search_content) {
        $nlp_fulltext = urldecode($search_content);

        $content = array();
        if (!$nlp_fulltext) {
            \Drupal::messenger()->addMessage(t('Invalid parameters'), 'error');
        } else {
            if (!empty($nlp_fulltext)) {

                $config = \Drupal::config('nlp_search.settings');
                $saved_python_flask_url = $config->get('nlp_search_basic_python_flask_url');

                if (!empty($saved_python_flask_url)) {
                    if ($saved_python_flask_url[strlen($saved_python_flask_url) - 1] != '/') {
                        $saved_python_flask_url .= '/';
                    }

                    $ch = curl_init();

                    //cUrl Aufruf an die Python Flask Anwendung
                    curl_setopt($ch, CURLOPT_URL, $saved_python_flask_url . "semantic-search");
                    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
                    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
                    curl_setopt($ch, CURLOPT_POST, 1);
                    curl_setopt($ch, CURLOPT_POSTFIELDS,
                        http_build_query(array('search_query' => json_encode($nlp_fulltext))));

                    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

                    $response = curl_exec($ch);

                    if ($response === FALSE) {
                        \Drupal::messenger()->addMessage(curl_error($ch), 'error');
                    } else {

                        //Fast analog zu der Funktion für die Filter wird geschaut auf welcher Seite der Suche sich der
                        //Anwender befindet, entsprechend werden diese Suchergebnisse aus dem Array geladen und das HTML-
                        //Gerüst zusammengebaut und gerendert.
                        $result_arr = json_decode($response, true);

                        if ($result_arr['type'] == 'success') {
                            if (count($result_arr['result']) == 0) {
                                $content[] = [
                                    '#markup' => '<p>' . t('No search results') . '</p>'
                                ];
                            } else {

                                $number_results = '<h3>' . t('@number results for "@search_query"', ['@number' => count($result_arr['result']), '@search_query' => $nlp_fulltext]) . '</h3>';
                                $content[] = [
                                    '#markup' => '<div class="nlp-search-results">' . $number_results
                                ];

                                $page = 0;
                                $num_per_page = 10;
                                if (isset($_GET['page'])) {
                                    $page = $_GET['page'];
                                }

                                $start = $num_per_page * $page;
                                $end = $start + $num_per_page;

                                pager_default_initialize(count($result_arr['result']), $num_per_page);

                                global $base_url;

                                for ($start; $start < $end; $start++) {

                                    if ($start >= count($result_arr['result'])) {
                                        break;
                                    }
                                    $html = '<li>';
                                    $html .= '<h3 class="nlp-search-result-title">';
                                    $html .= '<a href="' . $base_url . '/node/' . $result_arr['result'][$start]['node_id'] . '">' . $result_arr['result'][$start]['node_title'] . '</a>';
                                    $html .= '</h3>';
                                    $html .= '<div class="nlp-search-result-snippet-info">';
                                    $html .= '<p class="nlp-search-result-snippet">';
                                    $html .= '<span>';
                                    $html .= '<b>' . t('Changed') . '</b>: ' . date("Y-m-d H:i:s", $result_arr['result'][$start]['node_changed']) . ' | <b>' . t('Created') . '</b>: ' . date("Y-m-d H:i:s", $result_arr['result'][$start]['node_created']);
                                    $html .= '</span>';

                                    //Lieferte die semantische Ähnlichkeit Suchergebnisse, dann soll die Ähnlichkeit in Prozenten
                                    //ebenfalls mit angezeigt werden.
                                    if (isset($result_arr['result'][$start]['similarity'])) {
                                        $html .= '<span>';

                                        $sim = ($result_arr['result'][$start]['similarity'] * 100);
                                        $html .= '<b>' . t('Semantic similarity') . '</b>: ' . number_format($sim, 2) . ' %';
                                        $html .= '</span>';
                                    }

                                    $html .= '<span>';

                                    //Ein Suchergebnis kann zu einem gefundenen Hauptknoten bis zu 3 Sätzen enthalten.
                                    //Diese werden iteriert und zu einem String zusammengefügt.
                                    if (is_array($result_arr['result'][$start]['sents'])) {
                                        foreach ($result_arr['result'][$start]['sents'] as $item) {
                                            $html .= $item . ' ';

                                        }
                                    } else {
                                        $html .= $result_arr['result'][$start]['sents'];
                                    }
                                    $html .= '</span>';
                                    $html .= '</p>';
                                    $html .= '</div>';
                                    $html .= '</li>';

                                    $content[] = [
                                        '#markup' => $html,

                                    ];


                                }
                                $content[] = [
                                    '#markup' => '</div>'
                                ];

                                $content[] = ['#type' => 'pager'];
                                $content['#attached']['library'][] = 'nlp_search/nlpsearch_basic';

                            }
                        } else {
                            \Drupal::messenger()->addMessage($result_arr['result'], 'error');
                        }
                    }

                    curl_close($ch);
                } else {
                    \Drupal::messenger()->addMessage(t('Missing configuration python flask url'), 'error');
                }

            } else {
                \Drupal::messenger()->addMessage(t('Nothing to search for'), 'error');
            }
        }

        return $content;
    }
}