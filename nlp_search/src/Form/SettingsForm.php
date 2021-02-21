<?php
/**
 * Created by PhpStorm.
 * User: Corin
 * Date: 25.04.2019
 * Time: 18:15
 */

namespace Drupal\nlp_search\Form;

use Drupal\Core\Form\ConfigFormBase;
use Drupal\Core\Form\FormStateInterface;
use Drupal\node\Entity\NodeType;
use Drupal\node\Entity\Node;


class SettingsForm extends ConfigFormBase {
    //Name der Einstellung für dieses Modul definieren
    const SETTINGS = 'nlp_search.settings';

    public function getFormId() {
        return 'nlp_search_settings';
    }

    protected function getEditableConfigNames() {
        return [
            static::SETTINGS,
        ];
    }

    //Diese Funktion baut das Formular für die Einstellungsseite im Administrationsbereich zusammen.
    public function buildForm(array $form, FormStateInterface $form_state) {

        //Config laden und die abgespeicherten Content Types mit ihren Feldern.
        $config = $this->config(static::SETTINGS);
        $saved_content_types = json_decode($config->get('nlp_search_content_types'), true);

        //Anzahl aus form_state holen. Wenn ein Content Type Feld dynamisch durch Javascript erzeugt wird, wird die Zahl
        //um eins erhöht, damit beim erneuten Rendern des Formulars ein Feld mehr erzeugt wird. Gleiches gilt für das
        //Löschen eines Content Types Feldes.
        $num_field = $form_state->get('num_content_types');
        $form['#tree'] = TRUE;

        //Fieldset für den Indexstatus erzeugen. In diesem Fieldset werden die Anzahl der indexierten Knoten in der
        //Datenbank für einen Content Type angezeigt, die Anzahl der exportierten Knoten, die Anzahl der noch zu verarbeitenden Knoten und
        //die Anzahl der fehlgeschlagenen Knoten
        $form['index_fieldset'] = [
            '#type' => 'fieldset',
            '#title' => $this->t('Index status'),
        ];

        //Die unterschiedlichen Dateien öffnen, um die Anzahl der noch zu bearbeitenden Knoten, die Anzahl der exportierten
        //Knoten und die Anzahl der fehlgeschlagenen Knoten ermitteln zu können.
        $mod_path = drupal_get_path('module', 'nlp_search');
        $export_path = $mod_path . '/nlp_python/export';
        $export_file = $export_path . '/nodes_export.json';
        $nodes_export_arr = array();

        if (file_exists($export_file)) {
            $file = file_get_contents($export_file);
            $nodes_export_arr = json_decode($file, true);
        }

        $export_process_file = $export_path . '/nodes_export_process.json';
        $nodes_export_process_arr = array();

        if (file_exists($export_process_file)) {
            $file = file_get_contents($export_process_file);
            $nodes_export_process_arr = json_decode($file, true);
        }

        $nodes_failed_file = $export_path . '/nodes_failed.json';
        $nodes_failed_arr = array();

        if (file_exists($nodes_failed_file)) {
            $file = file_get_contents($nodes_failed_file);
            $nodes_failed_arr = json_decode($file, true);
        }

        $settings_revised = array();

        //In den geladenen Einstellungen steht in jeder Zeile des Arrays der Content Type und das Feld drin. Für den
        //weiteren einfacheren Umgang, werden die Einstellungen verändert, sodass jeder Content Type nur einmal in dem
        //Array vor kommt und ihm ein Array mit den Feldern zugewiesen ist.
        foreach ($saved_content_types as $setting) {
            if (!is_array($settings_revised[$setting['content_type']])) {
                $settings_revised[$setting['content_type']] = array();
            }

            array_push($settings_revised[$setting['content_type']], $setting['field']);
        }

        $saved_python_flask_url = $config->get('nlp_search_basic_python_flask_url');

        //Für jeden Content Type einen Aufruf an die Python Flask Anwendung schicken, um die Anzahl der Hauptknoten
        //zu bekommen, die diesem Content Type zugeordnet sind.
        foreach ($settings_revised as $content_type => $value) {

            $nodes_db_counter = '';
            if (!empty($saved_python_flask_url)) {
                if ($saved_python_flask_url[strlen($saved_python_flask_url) - 1] != '/') {
                    $saved_python_flask_url .= '/';
                }

                $ch = curl_init();

                curl_setopt($ch, CURLOPT_URL, $saved_python_flask_url . "get-nodes-count");
                curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
                curl_setopt($ch, CURLOPT_TIMEOUT, 10);
                curl_setopt($ch, CURLOPT_POST, 1);
                curl_setopt($ch, CURLOPT_POSTFIELDS,
                    http_build_query(array('content_type' => $content_type)));

                curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

                $response = curl_exec($ch);

                if ($response === FALSE) {
                    $nodes_db_counter = t('No connection to Neo4j');
                    \Drupal::messenger()->addMessage(curl_error($ch), 'error');
                } else {
                    $response = json_decode($response, true);
                    if ($response['type'] == 'success') {
                        $nodes_db_counter = $response['result'][0]['node_count'];
                    } else {
                        $nodes_db_counter = t('No connection to Neo4j');
                        \Drupal::messenger()->addMessage($response['result'], 'error');
                    }
                }

                curl_close($ch);

            } else {
                \Drupal::messenger()->addMessage(t('Missing configuration python flask url'), 'error');
            }

            $export_counter = 0;
            $export_process_counter = 0;
            $nodes_failed_counter = 0;

            //Wenn in den Dateien etwas drin steht, die entsprechenden Counter setzen.
            if (isset($nodes_export_arr[$content_type])) {
                $export_counter = count($nodes_export_arr[$content_type]);
            }

            if (isset($nodes_export_process_arr[$content_type])) {
                $export_process_counter = count($nodes_export_process_arr[$content_type]);
            }

            if (isset($nodes_failed_arr[$content_type])) {
                $nodes_failed_counter = count($nodes_failed_arr[$content_type]);
            }

            //Neuen Fieldset für jede Art von Content Type erstellen.
            $form['index_fieldset']['fieldset_' . $content_type] = [
                '#type' => 'fieldset',
                '#title' => $this->t('Content Type: @content_type', ['@content_type' => $content_type]),
            ];

            //HTML für das Markup zusammenbauen und dem Markup zuweisen.
            $html = t('Nodes in Neo4j Database: @nodes_counter', ['@nodes_counter' => $nodes_db_counter]). '<br>';
            $html .= t('Nodes exported: @nodes_counter', ['@nodes_counter' => $export_counter]). '<br>';
            $html .= t('Nodes not processed yet: @nodes_process_counter', ['@nodes_process_counter' => $export_process_counter]). '<br>';
            $html .= t('Nodes failed: @nodes_failed', ['@nodes_failed' => $nodes_failed_counter]). '<br>';

            $form['index_fieldset']['fieldset_' . $content_type]['info'] = [
                '#markup' => $html,
            ];

            //Fehlgeschlagene Knoten in einem eigenen Fieldset anzeigen lassen. Dadurch wird die Übersicht verbessert.
            if (count($nodes_failed_arr[$content_type]) > 0) {
                $form['index_fieldset']['fieldset_' . $content_type]['info']['failed'] = [
                    '#type' => 'fieldset',
                    '#title' => $this->t('Failed'),
                ];

                $html = '';

                //Eine Liste der fehlgeschlagenen Knoten für den Content Type zusammenbauen und an das Markup übergeben.
                foreach ($nodes_failed_arr[$content_type] as $key => $value) {
                    $html .= '<b>' . t('Node ID') . '</b>: ' . $key . ' | ' . '<b>' . t('Node Title') . '</b>: ' . $value['title'] . '<br>';
                }

                $form['index_fieldset']['fieldset_' . $content_type]['info']['failed'][text] = [
                    '#markup' => $html,
                ];
            }
        }

        //Zwei Buttons definieren, die beim Abschicken jeweils eine eigene Funktion aufrufen.
        $form['index_fieldset']['actions']['index_all'] = [
            '#type' => 'submit',
            '#value' => t('Index all'),
            '#submit' => array('::indexAll'),
        ];

        $form['index_fieldset']['actions']['reindex_failed'] = [
            '#type' => 'submit',
            '#value' => t('Reindex failed'),
            '#submit' => array('::reindexFailed'),
        ];

        //In einem weiteren Fieldset kann die Basic Configuration für das Modul vorgenommen werden.
        $saved_similarity_score = '';
        $saved_neo4j_url = '';
        $saved_neo4j_user = '';
        $saved_neo4j_password = '';
        $saved_corenlp_url = '';
        $saved_corenlp_port = '';

        //Bis auf die URL der Python Flask Anwendung, werden die restlichen Einstellungen in einer config.json gespeichert,
        //damit die Python Anwendungen darauf ebenfalls zugreifen können. Die URL der Python Anwendung wiederum wird nur
        //innerhalb des Moduls benötigt.
        $export_path = $mod_path . '/nlp_python';
        $config_file = $export_path . '/config.json';
        $config_arr = array();

        $file = "";
        if (file_exists($config_file)) {
            $file = file_get_contents($config_file);
            $config_arr = json_decode($file, true);
        }

        if (isset($config_arr['similarity_score'])) {
            $saved_similarity_score = $config_arr['similarity_score'];
        }

        if (isset($config_arr['neo4j_url'])) {
            $saved_neo4j_url = $config_arr['neo4j_url'];
        }

        if (isset($config_arr['neo4j_user'])) {
            $saved_neo4j_user = $config_arr['neo4j_user'];
        }

        if (isset($config_arr['neo4j_password'])) {
            $saved_neo4j_password = $config_arr['neo4j_password'];
        }

        if (isset($config_arr['corenlp_url'])) {
            $saved_corenlp_url = $config_arr['corenlp_url'];
        }

        if (isset($config_arr['corenlp_port'])) {
            $saved_corenlp_port = $config_arr['corenlp_port'];
        }

        //Fieldset definieren und die einzelnen Eingabefelder für die Konfigurationseinstellungen.
        $form['basic_fieldset'] = [
            '#type' => 'fieldset',
            '#title' => $this->t('Basic Configuration'),
        ];

        $form['basic_fieldset']['python_flask_url'] = [
            '#type' => 'textfield',
            '#title' => t('URL for python flask application'),
            '#default_value' => $saved_python_flask_url,
            '#description' => t('Define url with port. For example http://127.0.0.1:5000')
        ];

        $form['basic_fieldset']['corenlp_url'] = [
            '#type' => 'textfield',
            '#title' => t('Stanford CoreNLP URL'),
            '#default_value' => $saved_corenlp_url,
            '#description' => t('For example http://192.168.2.130')
        ];

        $form['basic_fieldset']['corenlp_port'] = [
            '#type' => 'textfield',
            '#title' => t('Stanford CoreNLP Port'),
            '#default_value' => $saved_corenlp_port,
            '#description' => t('For example 9000')
        ];

        $form['basic_fieldset']['similarity_score'] = [
            '#type' => 'textfield',
            '#title' => t('Score for similarity in search results'),
            '#default_value' => $saved_similarity_score,
            '#description' => t('For example 0.79 for 79%')
        ];

        $form['basic_fieldset']['neo4j_url'] = [
            '#type' => 'textfield',
            '#title' => t('URL for Neo4j Server'),
            '#default_value' => $saved_neo4j_url,
            '#description' => t('For example bolt://192.168.2.130:7687')
        ];

        $form['basic_fieldset']['neo4j_user'] = [
            '#type' => 'textfield',
            '#title' => t('Neo4j user'),
            '#default_value' => $saved_neo4j_user,
        ];

        $form['basic_fieldset']['neo4j_password'] = [
            '#type' => 'password',
            '#title' => t('Neo4j password'),
            '#default_value' => $saved_neo4j_password,
        ];

        //Einen weiteren Fieldset für die Auswahl der Content Types und Felder definieren. Anhand dieser Konfiguration
        //werden nur Nodes exportiert, die dem Content Type entsprechen und die die definierten Felder besitzen.
        $form['content_types_fieldset'] = [
            '#type' => 'fieldset',
            '#title' => $this->t('Select content types and fields which should be added to search index'),
            '#prefix' => '<div id="content-types-fieldset-wrapper">',
            '#suffix' => '</div>',
        ];

        //Die Felder, um die Content Types zu definieren, werden in einer Schleife erstellt. Beim Laden der Einstellungs-
        //seite und wenn sich bereits gespeicherte Content Types in der Datenbank befinden, wird $num_field die Anzahl der
        //gespeicherten Content Types zugewiesen. Andernfalls wird $num_field auf 1 gesetzt, damit auch nur ein Auswahlfeld
        //initial angezeigt wird.
        if (empty($num_field)) {
            if (count($saved_content_types) > 0) {
                $num_field = count($saved_content_types);
                $form_state->set('num_content_types', $num_field);
            } else {
                $num_field = 1;
                $form_state->set('num_content_types', $num_field);
            }
        }

        //Alle Typen von Content Types laden, die aktuell in der Drupal Instanz definiert sind.
        $all_content_types = NodeType::loadMultiple();

        $content_type_arr = array("default" => t('- Select -'));

        //Alle vorhandenen Content Types iterieren.
        foreach ($all_content_types as $machine_name => $content_type) {

            //Die Felder einen Content Types laden
            (array)$nodes = \Drupal::service('entity_field.manager')->getFieldDefinitions('node', $machine_name);

            $has_correct_type = false;

            //Für die Auswahlliste sollen nur Content Types mit aufgenommen werden, die zum einen überhaupt Felder besitzen
            //und die Felder entsprechenden Typen entsprechen, die wiederum Text abspeichern können. Irgendwelche Felder
            //mit Bildern oder ähnlichem haben keinen Sinn.
            foreach ($nodes as $key => $value) {
                if (property_exists($value, 'field_type')) {
                    if ($value->get('field_type') == 'string' || $value->get('field_type') == 'text_long' || $value->get('field_type') == 'text_with_summary') {
                        $has_correct_type = true;
                    }
                }
            }

            //Hat ein Content Type Felder, die Text beinhalten können, diese dem Array content_type_arr hinzufügen.
            //Dieses Array wird weiter unten dem Auswahlfeld als Auswahlmöglichkeiten zugewiesen.
            if ($has_correct_type) {
                $label = $content_type->label();
                $content_type_arr[$machine_name] = $label;
            }

        }

        //Die Anzahl von num_field iterieren, um die Auswahlfelder zu erstellen. Dieser Vorgang geschieht beim Aufrufen
        //der Einstellungsseite, aber auch beim dynamischen Hinzufügen von weiteren Auswahlfeldern, da genau diese
        //Funktion wieder aufgerufen, das Formular neu zusammengebaut und im HTML DOM durch das alte Formular ersetzt wird.
        for ($i = 0; $i < $num_field; $i++) {

            //Jeden Auswahlbereich für einen Content Type in einem eigenen Fielset anzeigen lassen.
            $form['content_types_fieldset'][$i]['select_fieldset'] = [
                '#type' => 'fieldset',
                '#prefix' => '<div id="select-fieldset-wrapper">',
                '#suffix' => '</div>',
            ];

            $content_type_value = 'default';
            $field_value = 'default';

            //Werden dynamisch neue Auswahlfelder erzeugt, so stehen in form_state die bisher definierten Felder drin.
            //Das Formular wird komplett neu erstellt und damit die bisher definierten Felder wieder erstellt werden können,
            //wird aus form_state der gesetzte Wert ausgelesen und dem Auswahlfeld wieder zugewiesen.
            if ($form_state->getValue('content_types_fieldset') !== null) {
                $content_type_value = $form_state->getValue(['content_types_fieldset', $i, 'select_fieldset', 'content_type']);

                $field_value = $form_state->getValue(['content_types_fieldset', $i, 'select_fieldset', 'field']);
            } else {

                //Beim Laden der Einstellungsseite stehen in form_state logischerweise keine Werte für Content Type Felder.
                //Allerdings können Auswahlfelder für Content Types bereits einmal abgespeichert worden sein und diese
                //sollen nun wieder angezeigt werden. Somit aus dem Array saved_content_types, das aus der Datenbank
                //geladen wurde, die gesetzten Werte für den Content Type und dem Feld auslesen, damit diese wieder den
                //Auswahlfeldern zugewiesen werden können.
                if (count($saved_content_types) > 0) {
                    $content_type_value = $saved_content_types[strval($i)]['content_type'];
                    $field_value = $saved_content_types[strval($i)]['field'];
                }
            }

            $form['content_types_fieldset'][$i]['select_fieldset']['content_type'] = [
                '#type' => 'select',
                '#title' => $this->t('Select content type'),
                '#default_value' => $content_type_value,
                '#options' => $content_type_arr,
                '#ajax' => [
                    'callback' => '::addmoreCallback',
                    'event' => 'change',
                    'wrapper' => 'content-types-fieldset-wrapper'
                ],
            ];

            //Ist content_type_value gesetzt und steht nicht auf default, für den Content Type die Felder laden und einem
            //Array hinzufügen, das dem Auswahlfeld für die Felder zugewiesen werden kann. Die Variable ist gesetzt, wenn
            //bereits in der Datenbank Content Types gespeichert wurden oder auch wenn dynamisch ein neues Auswahlfeld
            //hinzugefügt werden soll und es bereits andere gesetzte Felder gibt.
            if (isset($content_type_value) && $content_type_value !== 'default') {

                (array)$nodes = \Drupal::service('entity_field.manager')->getFieldDefinitions('node', $content_type_value);

                $fields_arr = array('default' => t('- select -'));

                foreach ($nodes as $key => $value) {
                    if (property_exists($value, 'field_type')) {
                        if ($value->get('field_type') == 'string' || $value->get('field_type') == 'text_long' || $value->get('field_type') == 'text_with_summary') {
                            $fields_arr[$value->get('field_name')] = $value->get('label');
                        }
                    }
                }

                $form['content_types_fieldset'][$i]['select_fieldset']['field'] = [
                    '#type' => 'select',
                    '#title' => $this->t('Select field'),
                    '#default_value' => $field_value,
                    '#options' => $fields_arr,

                ];
            }
        }

        //Nach dem Hinzufügen der Auswahlfelder die Buttons noch hinzufügen.
        $form['actions'] = [
            '#type' => 'actions',
        ];
        $form['content_types_fieldset']['actions']['add_name'] = [
            '#type' => 'submit',
            '#value' => t('Add one more'),
            '#submit' => array('::addOne'),
            '#ajax' => [
                //Callback gibt den Teil des Formular-Arrays zurück, in dem die Felder für die Content Types erzeugt
                //wurden der wrapper gibt an, welches HTML-Element mit der definierten Klasse das neue Formular zugewiesen
                //bekommt. Die Funktion addOne wiederum erhöht num_field um eins und gibt an, dass das Formular neu
                //aufgebaut werden soll.
                'callback' => '::addmoreCallback',
                'wrapper' => 'content-types-fieldset-wrapper',
            ],
        ];

        //Der Löschen-Button soll nur angezeigt werden, wenn es mehr als ein Auswahlfeld für einen Content Type gibt.
        if ($num_field > 1) {
            $form['content_types_fieldset']['actions']['remove_name'] = [
                '#type' => 'submit',
                '#value' => t('Remove one'),
                '#submit' => array('::removeCallback'),
                '#ajax' => [
                    'callback' => '::addmoreCallback',
                    'wrapper' => 'content-types-fieldset-wrapper',
                ],
            ];
        }
        $form_state->setCached(FALSE);
        $form['actions']['submit'] = [
            '#type' => 'submit',
            '#value' => $this->t('Submit'),
        ];

        return $form;
    }

    //Funktion wird aufgerufen, wenn der entsprechende Button betätigt wurde.
    public function reindexFailed(array &$form, FormStateInterface $form_state) {

        //Datei laden, zu der die fehlgeschlagenen Nodes wieder hinzugefügt werden sollen.
        $mod_path = drupal_get_path('module', 'nlp_search');
        $export_path = $mod_path . '/nlp_python/export';
        $export_file = $export_path . '/nodes_export.json';
        $nodes_arr = array();

        if (!is_dir($export_path)) {
            mkdir($export_path);
        }

        $file = "";
        if (file_exists($export_file)) {
            $file = file_get_contents($export_file);
            $nodes_arr = json_decode($file, true);
        }

        //Datei mit den fehlgeschlagenen Nodes laden.
        $failed_file = $export_path . '/nodes_failed.json';
        $nodes_failed_arr = array();

        $file = "";
        if (file_exists($failed_file)) {
            $file = file_get_contents($failed_file);
            $nodes_failed_arr = json_decode($file, true);
        }

        $config = $this->config(static::SETTINGS);
        $saved_content_types = json_decode($config->get('nlp_search_content_types'), true);

        $settings_revised = array();

        //Array mit den Einstellungen aus der Datenbank umändern, damit besser mit den gesetzen Einstellungen weiter
        //gearbeitet werden kann.
        foreach ($saved_content_types as $setting) {
            if (!is_array($settings_revised[$setting['content_type']])) {
                $settings_revised[$setting['content_type']] = array();
            }

            array_push($settings_revised[$setting['content_type']], $setting['field']);
        }

        //Alle fehlgeschlagenen Content Types aus der Datei der fehlgeschlagenen Nodes iterieren.
        foreach ($nodes_failed_arr as $content_type => $nodes) {

            //Zu jedem Content Type die fehlgeschlagenen Nodes iterieren.
            foreach ($nodes as $nid => $value) {
                if (isset($nodes_arr[$content_type][$nid])) {
                    unset($nodes_arr[$content_type][$nid]);
                }

                //Fehlgeschlagene Node kann entfernt werden.
                unset($nodes_failed_arr[$content_type][$nid]);

                //Die Node laden und zu der Node den Inhalt der Felder laden, die vorher auf der Einstellungsseite festgelegt wurden.
                $node = Node::load($nid);

                $created = $node->get('created')->getValue()[0]['value'];
                $changed = $node->get('changed')->getValue()[0]['value'];

                $has_content = false;
                foreach ($settings_revised[$content_type] as $field) {
                    $node_field = $node->get($field)->getValue();

                    foreach ($node_field as $index => $field_entry) {

                        if (!empty(trim($field_entry['value']))) {
                            $nodes_arr[$content_type][$nid]['title'] = $node->title->value;
                            $nodes_arr[$content_type][$nid]['fields'][$field][$index] = preg_replace('/\s+/S', " ", $field_entry['value']);
                            $has_content = true;
                        }

                    }
                }

                if ($has_content){

                    $nodes_arr[$content_type][$nid]['created'] = $created;
                    $nodes_arr[$content_type][$nid]['changed'] = $changed;

                }

            }

            //Existieren für den Content Type keine fehlgeschlagene Nodes mehr, kann dieser ebenfalls aus dem Array entfernt werden.
            if (count($nodes_failed_arr[$content_type]) == 0) {
                unset($nodes_failed_arr[$content_type]);
            }
        }

        //Beide Dateien wieder speichern und eine Meldung ausgeben.
        file_put_contents($export_file, json_encode($nodes_arr, JSON_UNESCAPED_UNICODE));
        file_put_contents($failed_file, json_encode($nodes_failed_arr, JSON_UNESCAPED_UNICODE));

        \Drupal::messenger()->addMessage(t('Nodes exported for reindexing'));
    }

    //Diese Funktion wird aufgerufen, wenn der entsprechende Button betätigt wurde.
    public function indexAll(array &$form, FormStateInterface $form_state) {

        //Festgelegte gespeicherte Content Types aus der Datenbank laden, für die und deren Felder Nodes exportiert werden sollen.
        $nodes_counter = array();
        $config = $this->config(static::SETTINGS);
        $saved_content_types = json_decode($config->get('nlp_search_content_types'), true);

        $settings_revised = array();

        //Datei für die exportierten Nodes laden, damit die neuen zu exportierenden Nodes in das Array eingefügt werden können.
        $mod_path = drupal_get_path('module', 'nlp_search');
        $export_path = $mod_path . '/nlp_python/export';
        $export_file = $export_path . '/nodes_export.json';
        $nodes_arr = array();

        if (!is_dir($export_path)) {
            mkdir($export_path);
        }

        $file = "";
        if (file_exists($export_file)) {
            $file = file_get_contents($export_file);
            $nodes_arr = json_decode($file, true);
        }

        //Array mit den Einstellungen aus der Datenbank umändern, damit besser mit den gesetzen Einstellungen weiter
        //gearbeitet werden kann.
        foreach ($saved_content_types as $setting) {
            if (!is_array($settings_revised[$setting['content_type']])) {
                $settings_revised[$setting['content_type']] = array();
            }

            array_push($settings_revised[$setting['content_type']], $setting['field']);
        }

        //Jeden gespeicherten Content Type iterieren
        foreach ($settings_revised as $content_type => $fields) {

            //Counter initialisieren, der am Ende anzeigt, wie viele Nodes zu einem Content Type gefunden und exportiert wurden.
            $nodes_counter[$content_type]['nodes_counter'] = 0;

            //Nodes, die dem Content Type entsprechen und published sind, laden.
            $nids = \Drupal::entityQuery('node')
                ->condition('status', 1)
                ->condition('type', $content_type)
                ->execute();


            //Jede Node iterieren, den Inhalt der Felder laden und im Array abspeichern.
            foreach ($nids as $nid) {


                if (isset($nodes_arr[$content_type][$nid])) {
                    unset($nodes_arr[$content_type][$nid]);
                }

                $node = Node::load($nid);

                $created = $node->get('created')->getValue()[0]['value'];
                $changed = $node->get('changed')->getValue()[0]['value'];

                $has_content = false;
                foreach ($fields as $field) {
                    $node_field = $node->get($field)->getValue();

                    foreach ($node_field as $index => $field_entry) {

                        if (!empty(trim($field_entry['value']))) {
                            $nodes_arr[$content_type][$nid]['title'] = $node->title->value;
                            $nodes_arr[$content_type][$nid]['fields'][$field][$index] = preg_replace('/\s+/S', " ", $field_entry['value']);
                            $has_content = true;
                        }

                    }
                }

                if ($has_content){

                    $nodes_arr[$content_type][$nid]['created'] = $created;
                    $nodes_arr[$content_type][$nid]['changed'] = $changed;

                    $nodes_counter[$content_type]['nodes_counter']++;
                }
            }
        }

        //Datei mit exportierten Nodes abspeichern und eine Meldung anzeigen, wie viele Nodes für den entsprechenden
        //Content Type exportiert wurden.
        file_put_contents($export_file, json_encode($nodes_arr, JSON_UNESCAPED_UNICODE));


        foreach ($nodes_counter as $content_type => $value) {
            \Drupal::messenger()->addMessage(t('Queued "@counter" nodes for content type "@content_type"', ['@counter' => $value['nodes_counter'], '@content_type' => $content_type]));
        }
    }

    //Nachdem Aufruf von Javascript zum neu erstellen des Formulars, gibt diese Funktion den Teil des Formulars
    //für die Content Types zurück, was wiederum mit dem alten Formular im definierten Wrapper ersetzt wird.
    public function addmoreCallback(array &$form, FormStateInterface $form_state) {
        return $form['content_types_fieldset'];
    }

    //Funktion wird von Javascript aufgerufen, um ein neues Auswahlfeld für Content Types zu erzeugen. Dafür den Zähler
    //um eins erhöhen, damit beim neu erstellen des Fomulars ein zusätzliches Auswahlfeld erzeugt wird.
    public function addOne(array &$form, FormStateInterface $form_state) {
        $num_field = $form_state->get('num_content_types');
        $add_button = $num_field + 1;
        $form_state->set('num_content_types', $add_button);
        $form_state->setRebuild();
    }

    //Funktion wird von Javascript aufgerufen, um das letztes Auswahl eines Content Types zu entferne. Dafür wird der
    //Zähler um eins verringert, sodass beim neu erstellen des Formulars ein Auswahlfeld weniger angezeigt wird.
    public function removeCallback(array &$form, FormStateInterface $form_state) {
        $num_field = $form_state->get('num_content_types');
        if ($num_field > 1) {
            $remove_button = $num_field - 1;
            $form_state->set('num_content_types', $remove_button);
        }
        $form_state->setRebuild();
    }

    //Diese Funktion speichert die eingetragenen Einstellung in der Datenbank und in der config.json
    public function submitForm(array &$form, FormStateInterface $form_state) {
        $content_types = $form_state->getValue('content_types_fieldset');
        $result = array();

        $counter = 0;

        //Alle in form_state gesetzten Content Types iterieren, dem Array zuweisen, das im Anschluss als Json in der
        //Datenbank gespeichert wird.
        foreach ($content_types as $key => $value) {
            if ($key !== 'actions') {
                if ($value['select_fieldset']['content_type'] !== 'default') {

                    if ($value['select_fieldset']['field'] !== 'default') {

                        $add = true;
                        foreach ($result as $res) {
                            if ($res['content_type'] == $value['select_fieldset']['content_type']
                                && $res['field'] == $value['select_fieldset']['field']) {

                                $add = false;
                            }
                        }

                        if ($add) {
                            $result[$counter]['content_type'] = $value['select_fieldset']['content_type'];
                            $result[$counter]['field'] = $value['select_fieldset']['field'];

                            $counter++;
                        }
                    }
                }

            }
        }

        //Content Types und URL für Python Flask Anwendung in der Datenbank speichern.
        $this->config(static::SETTINGS)
            ->set('nlp_search_content_types', json_encode($result))
            ->save();


        $basic = $form_state->getValue('basic_fieldset');
        $this->config(static::SETTINGS)
            ->set('nlp_search_basic_python_flask_url', $basic['python_flask_url'])
            ->save();



        //Konfigurationsdatei laden und die Werte zuweisen.
        $mod_path = drupal_get_path('module', 'nlp_search');
        $export_path = $mod_path . '/nlp_python';
        $config_file = $export_path . '/config.json';
        $config_arr = array();

        if (file_exists($config_file)) {
            $file = file_get_contents($config_file);
            $config_arr = json_decode($file, true);
        }


        $config_arr['similarity_score'] = $basic['similarity_score'];
        $config_arr['neo4j_url'] = $basic['neo4j_url'];
        $config_arr['neo4j_user'] = $basic['neo4j_user'];
        $config_arr['corenlp_url'] = $basic['corenlp_url'];
        $config_arr['corenlp_port'] = $basic['corenlp_port'];

        //Ein Passwortfeld kann keine default_value haben und würde somit beim Neuladen des Formulars leer sein. Damit
        //beim Abspeichern nicht jedes mal das Passwort erneut eingegeben werden muss, da ansonsten nur ein leerer String
        //als Passwort gespeichert wird, findet eine Speicherung nur statt, wenn in dem Feld auch ein Passwort eingetragen
        //wurde.
        if (!empty($basic['neo4j_password'])) {
            $config_arr['neo4j_password'] = $basic['neo4j_password'];
        }

        file_put_contents($config_file, json_encode($config_arr, JSON_UNESCAPED_UNICODE));

        //Die Tabs zum Editieren und Hinzufügen von Entitäten werden nur angezeigt, die Node einem der auf der
        //Einstellungsseite gespeicherten Content Types entspricht. Bei den Einstellungen für Routen ist eine zusätzliche
        //Überprüfung durch CheckAccessController definiert, die den Content Type überprüft. Diese Routen werden gecacht.
        //Damit nicht jedes mal manuell der Cache nach dem Ändern von Content Types auf dieser Einstellungsseite gelöscht
        //werden muss, findet ein Rebuild der Routen beim Speichern statt.
        \Drupal::service('router.builder')->rebuild();
        parent::submitForm($form, $form_state);

    }
}