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

class EditEntitiesForm extends FormBase
{

    /**
     * {@inheritdoc}
     */
    public function getFormId()
    {
        return 'nlp_search_edit_entities_form';
    }

    //Die Funktion baut das Formular für das Editieren von Entitäten auf
    public function buildForm(array $form, FormStateInterface $form_state)
    {
        
        $form = array();
        $config = \Drupal::config('nlp_search.settings');
        $saved_python_flask_url = $config->get('nlp_search_basic_python_flask_url');

        if (!empty($saved_python_flask_url)) {
            if ($saved_python_flask_url[strlen($saved_python_flask_url) - 1] != '/') {
                $saved_python_flask_url .= '/';
            }
            $node_id = \Drupal::routeMatch()->getParameter('node');

            //cUrl Aufruf, um von Python Flask Anwendung alle Entitäten zu einer Drupal Node ID zu bekommen
            $ch = curl_init();
            curl_setopt($ch, CURLOPT_URL, $saved_python_flask_url . "get-entities-by-id");
            curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
            curl_setopt($ch, CURLOPT_TIMEOUT, 10);
            curl_setopt($ch, CURLOPT_POST, 1);
            curl_setopt($ch, CURLOPT_POSTFIELDS,
                http_build_query(array('node_id' => $node_id)));

            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            $response = curl_exec($ch);

            if ($response === FALSE) {
                \Drupal::messenger()->addMessage(curl_error($ch), 'error');
            } else {


                $entities = json_decode($response, true);

                if ($entities['type'] == 'success') {

                    if (count($entities['result']) == 0) {
                        $form['default'] = [
                            '#markup' => '<p>' . t('No entities for this node') . '</p>',
                        ];
                    } else {

                        $form['#tree'] = TRUE;

                        $counter = 0;

                        //Für jede Entität die Formularfelder bauen
                        foreach ($entities['result'] as $ent) {
                            //dsm($ent);
                            $form['entities']['entity' . $counter] = [
                                '#type' => 'fieldset',
                                '#title' => $ent['ent_text'],
                            ];
                            $form['entities']['entity' . $counter]['ner'] = [
                                '#type' => 'textfield',
                                '#default_value' => $ent['ent_ner'],
                                '#autocomplete_route_name' => 'nlp_search.autocomplete.entity.type',
                            ];

                            $form['entities']['entity' . $counter]['text'] = [
                                '#type' => 'hidden',
                                '#value' => $ent['ent_text']
                            ];

                            $form['entities']['entity' . $counter]['delete'] = [
                                '#type' => 'checkbox',
                                '#title' => t('Delete. Can not be undone.'),
                            ];

                            $counter++;
                        }

                        $form['actions'] = [
                            '#type' => 'actions',
                        ];

                        $form['actions']['submit'] = [
                            '#type' => 'submit',
                            '#value' => $this->t('Save'),
                            '#attributes' => array('style' => array('margin-left: 0px;'))
                        ];
                    }
                } else {
                    \Drupal::messenger()->addMessage($entities['result'], 'error');
                }
            }
            curl_close($ch);
        } else {
            \Drupal::messenger()->addMessage(t('Missing configuration python flask url'), 'error');
        }
        return $form;
    }

    public function validateForm(array &$form, FormStateInterface $form_state)
    {

        //Überprüfen, ob bei allen Entitäten der Text definiert ist ansonsten eine Fehlermeldung ausgeben.
        $entities = $form_state->getValue('entities');
        foreach ($entities as $key => $value) {
            if (empty($value['ner']) && $value['delete'] == 0) {
                $form_state->setErrorByName("entities][$key][ner",
                    t('Please enter a value!'));
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
            $entities = $form_state->getValue('entities');

            //Das Array mit Entitäten an die Python Flask Anwendung schicken, die die Änderungen in der Datenbank speichert.
            $ch = curl_init();
            curl_setopt($ch, CURLOPT_URL, $saved_python_flask_url. "change-entities");
            curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
            curl_setopt($ch, CURLOPT_TIMEOUT, 10);
            curl_setopt($ch, CURLOPT_POST, 1);
            curl_setopt($ch, CURLOPT_POSTFIELDS,
                http_build_query(array('entities' => json_encode($entities))));

            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            $response = curl_exec($ch);

            if ($response === FALSE) {
                \Drupal::messenger()->addMessage(curl_error($ch), 'error');
            } else {

                $response = json_decode($response, true);
                if ($response['type'] == 'success') {
                    \Drupal::messenger()->addMessage(t('Saved changes'));

                    //Wurden Entitäten gelöscht, so werden diese in changed_entities.json festgehalten, damit beim nächsten
                    //automatischen Indexieren und Extrahieren von Informationen, diese Entitäten nicht wieder mit
                    //angelegt werden, falls es sich bei den gelöschten Entitäten um Entitäten handelt, die von CoreNLP
                    //extrahiert wurden.
                    $changed_entities_path = drupal_get_path('module', 'nlp_search') . '/nlp_python/changed_entities.json';
                    $changed_entities = array();
                    if (file_exists($changed_entities_path)) {
                        $file = file_get_contents($changed_entities_path);
                        $changed_entities = json_decode($file, true);
                    }

                    if (!is_array($changed_entities['removed_entities'])) {
                        $changed_entities['removed_entities'] = array();
                    }

                    foreach ($entities as $ent) {
                        if ($ent['delete'] == 1) {
                            $changed_entities['removed_entities'][] = $ent['text'];

                            //Falls gelöscht Entitäten in added_entities stehen, diese dort wieder entfernen.
                            if (isset($changed_entities['added_entities'][$ent['text']])) {
                                unset($changed_entities['added_entities'][$ent['text']]);
                            }
                        }
                    }

                    file_put_contents($changed_entities_path, json_encode($changed_entities, JSON_UNESCAPED_UNICODE));
                }

                else {
                    \Drupal::messenger()->addMessage($response['result'], 'error');
                }
            }
        } else {
            \Drupal::messenger()->addMessage(t('Missing configuration python flask url'), 'error');
        }
    }

}
