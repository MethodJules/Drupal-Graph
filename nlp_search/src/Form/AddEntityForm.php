<?php
/**
 * Created by PhpStorm.
 * User: Corin
 * Date: 28.05.2019
 * Time: 18:10
 */

namespace Drupal\nlp_search\Form;

use Drupal\Core\Form\FormBase;
use Drupal\Core\Form\FormStateInterface;
use Symfony\Component\HttpFoundation\RedirectResponse;

class AddEntityForm extends FormBase
{

    /**
     * {@inheritdoc}
     */
    public function getFormId()
    {
        return 'nlp_search_add_entity_form';
    }

    //Formular zum Hinzufügen von neuen Entitäten erstellen.
    public function buildForm(array $form, FormStateInterface $form_state)
    {

        $form['#tree'] = TRUE;

        //Formularfelder definieren.
        $form['add_entity'] = [
            '#type' => 'fieldset',
            '#title' => 'Add Entity',
        ];

        $form['add_entity']['entity_text'] = [
            '#type' => 'textfield',
            '#title' => t('Entity text'),
            '#description' => t('Define text of entity, like a name, city, country, etc. The system will look in each node if this text exists and will map it to the entity.')
        ];

        $form['add_entity']['entity_ner'] = [
            '#type' => 'textfield',
            '#title' => t('Entity NER'),
            '#description' => t('Define named entity recognition, like PERSON, CITY, COUNTRY, etc.')
        ];

        $form['actions'] = [
            '#type' => 'actions',
        ];

        $form['actions']['submit'] = [
            '#type' => 'submit',
            '#value' => $this->t('Save'),
        ];

        return $form;
    }

    public function validateForm(array &$form, FormStateInterface $form_state)
    {
        $entity = $form_state->getValue('add_entity');

        //Überprüfen, ob Text in die Felder eingegeben wurde. Wenn nicht, eine entsprechende Fehlermeldung ausgeben und die
        //Felder optisch hervorheben.
        $check = true;
        if (empty($entity['entity_text'])) {
            $check = false;
            $form_state->setErrorByName("add_entity][entity_text",
                t('Please enter a value!'));
        }

        if (empty($entity['entity_ner'])) {
            $check = false;
            $form_state->setErrorByName("add_entity][entity_ner",
                t('Please enter a value!'));
        }

        if ($check) {

            $config = \Drupal::config('nlp_search.settings');
            $saved_python_flask_url = $config->get('nlp_search_basic_python_flask_url');
            if (!empty($saved_python_flask_url)) {
                if ($saved_python_flask_url[strlen($saved_python_flask_url) - 1] != '/') {
                    $saved_python_flask_url .= '/';
                }

                //Überprüfen, ob die Entität bereits in der Datenbank existiert und falls ja eine Meldung ausgeben
                //und die Felder optisch hervorheben.
                $ch = curl_init();
                curl_setopt($ch, CURLOPT_URL, $saved_python_flask_url. "check-entity-exists");
                curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
                curl_setopt($ch, CURLOPT_TIMEOUT, 10);
                curl_setopt($ch, CURLOPT_POST, 1);
                curl_setopt($ch, CURLOPT_POSTFIELDS,
                    http_build_query(array('entity' => $entity['entity_text'])));

                curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
                $response = curl_exec($ch);

                if ($response === FALSE) {
                    \Drupal::messenger()->addMessage(curl_error($ch), 'error');
                } else {

                    $response = json_decode($response, true);

                    if ($response['type'] == 'success') {
                        if ($response['result'] == 'true') {
                            $form_state->setErrorByName("add_entity][entity_text",
                                t('Entity already exists!'));
                        }

                    } else {
                        $form_state->setErrorByName("add_entity][entity_text",
                            $response['result']);
                    }
                }
                curl_close($ch);
            } else {
                \Drupal::messenger()->addMessage(t('Missing configuration python flask url'), 'error');
            }

        }


    }

    public function submitForm(array &$form, FormStateInterface $form_state)
    {
        $config = \Drupal::config('nlp_search.settings');
        $saved_python_flask_url = $config->get('nlp_search_basic_python_flask_url');
        if (!empty($saved_python_flask_url)) {
            if ($saved_python_flask_url[strlen($saved_python_flask_url) - 1] != '/') {
                $saved_python_flask_url .= '/';
            }

            //Entität an die Python Flask Anwendung schicken, die diese wiederum in der Datenbank speichert.
            $entity = $form_state->getValue('add_entity');
            $ch = curl_init();
            curl_setopt($ch, CURLOPT_URL, $saved_python_flask_url . "add-entity");
            curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
            curl_setopt($ch, CURLOPT_TIMEOUT, 10);
            curl_setopt($ch, CURLOPT_POST, 1);
            curl_setopt($ch, CURLOPT_POSTFIELDS,
                http_build_query(array('entity_ner' => $entity['entity_ner'], 'entity_text' => $entity['entity_text'])));

            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            $response = curl_exec($ch);

            if ($response === FALSE) {
                \Drupal::messenger()->addMessage(curl_error($ch), 'error');
            } else {

                $result = json_decode($response, true);

                if ($result['type'] == 'success') {

                    //Die Python Anwendung schaut, ob es Sätze gibt, in denen die Entität vor kommt. Wenn dies nicht der
                    //Fall ist, dann wurde die Entität nicht in der Datenbank hinzugefügt und es soll eine entsprechende
                    //Meldung zurückgegeben werden.
                    if (count($result['result']) == 0) {
                        \Drupal::messenger()->addMessage(t('Could not found nodes with entity @ent_text. Entity not saved.',
                            ['@ent_text' => $entity['entity_text']]), 'error');
                    } else {

                        //Manuell hinzugefügte Entitäten sollten beim erneuten Indexieren von Nodes den Hauptknoten in Neo4j
                        //wieder zugeordnet werden können. Dafür werden die Entitäten in einem Json abgespeichert, das
                        //von Python geladen werden kann.
                        $changed_entities_path = drupal_get_path('module', 'nlp_search') . '/nlp_python/changed_entities.json';

                        $changed_entities = array();
                        if (file_exists($changed_entities_path)) {
                            $file = file_get_contents($changed_entities_path);
                            $changed_entities = json_decode($file, true);
                        }

                        if (!is_array($changed_entities['added_entities'])) {
                            $changed_entities['added_entities'] = array();
                        }

                        //Entität dem Array hinzufügen.
                        $changed_entities['added_entities'][$entity['entity_text']] = $entity['entity_ner'];

                        //Falls die Entität in dem Bereich der gelöschten Entitäten innerhalb des Arrays sich
                        //befindet, diese Entität dort enfernen.
                        if (array_search($entity['entity_text'], $changed_entities['removed_entities']) !== false) {
                            unset($changed_entities['removed_entities'][array_search($entity['entity_text'], $changed_entities['removed_entities'])]);
                        }

                        //Datei wieder abspeichern.
                        file_put_contents($changed_entities_path, json_encode($changed_entities, JSON_UNESCAPED_UNICODE));

                        $host = \Drupal::request()->getSchemeAndHttpHost();

                        //Die Python Anwendung liefert ein Array zurück, in dem alle Hauptknoten enthalten sind, bei denen
                        //die Entität gefunden wurde. Dieses Array iterieren und als Nachricht darstellen, welche Haupt-
                        //knoten alle gefunden wurden.
                        foreach ($result['result'] as $res) {

                            $message_start = '<a href="' . $host . '/node/' . $res['node_id'] . '">' . $res['node_title'] . '</a> ';
                            $message_end = t('has entity @ent_text (@ent_ner)',
                                ['@ent_text' => $res['ent_text'], '@ent_ner' => $res['ent_ner']]);
                            $rendered_message = \Drupal\Core\Render\Markup::create($message_start . $message_end);

                            \Drupal::messenger()->addMessage($rendered_message);

                        }
                    }
                } else {
                    \Drupal::messenger()->addMessage($result['result'], 'error');
                }

            }
            curl_close($ch);
        } else {
            \Drupal::messenger()->addMessage(t('Missing configuration python flask url'), 'error');
        }

    }
}