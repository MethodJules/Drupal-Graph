<?php
/**
 * Created by PhpStorm.
 * User: Corin
 * Date: 25.04.2019
 * Time: 18:46
 */

namespace Drupal\nlp_search\Form;

use Drupal\Core\Form\FormBase;
use Drupal\Core\Form\FormStateInterface;
use Symfony\Component\HttpFoundation\RedirectResponse;

class SearchForm extends FormBase
{

    /**
     * {@inheritdoc}
     */
    public function getFormId()
    {
        return 'nlp_search_search_form';
    }

    //Die Funktion baut das Suchformular zusammen.
    public function buildForm(array $form, FormStateInterface $form_state) {


        $form['description'] = [
            '#type' => 'item',
            '#markup' => $this->t('Use filter or fulltext search'),
        ];

        $config = \Drupal::config('nlp_search.settings');
        $saved_python_flask_url = $config->get('nlp_search_basic_python_flask_url');

        if (!empty($saved_python_flask_url)) {
            if ($saved_python_flask_url[strlen($saved_python_flask_url) - 1] != '/') {
                $saved_python_flask_url .= '/';
            }

            //cUrl Aufruf, um von der Python Flask Anwendung alle Entitäten zu erhalten. Diese werden an das Javascript
            //weitergereicht, um dort dynamisch Entiäten und deren Texte laden zu können.
            $ch = curl_init();
            curl_setopt($ch, CURLOPT_URL, $saved_python_flask_url . 'get-entities');
            curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
            curl_setopt($ch, CURLOPT_TIMEOUT, 10);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            $response = curl_exec($ch);


            if ($response === FALSE) {
                \Drupal::messenger()->addMessage(curl_error($ch), 'error');
            } else {
                $entities = json_decode($response, true);

                if ($entities['type'] == 'success') {
                    if (isset($entities['result']['types'])) {
                        //Entitäten anhand der Schlüssel vom Array sortieren
                        ksort($entities['result']['types']);

                        //Alle Texte der Entitäten sortieren
                        foreach ($entities['result']['types'] as $key => $value) {
                            sort($entities['result']['types'][$key]);
                        }

                    }

                    //Relationen sortieren
                    if (isset($entities['result']['relationships'])) {
                        sort($entities['result']['relationships']);
                    }

                    //Formular zusammenbauen
                    $form['nlp_fulltext'] = [
                        '#type' => 'textfield',
                        '#title' => $this->t('Fulltext'),
                        '#description' => $this->t('Enter searchphrase in natural language or several keywords. Leave fulltext empty if you want to search with filters.'),
                    ];

                    $form['seperator'] = [
                        '#markup' => '<hr>'
                    ];

                    $form['filter_title'] = [
                        '#type' => 'inline_template',
                        '#template' => '<span class="filter-title">' . $this->t('Filter') . '</span>',
                    ];

                    $form['nlp_filter_box'] = [
                        '#markup' => '<div id="nlpsearch-filter-box"></div>'
                    ];

                    //Librarys laden und die Entitäten an das Javascript übergeben.
                    $form['#attached']['library'][] = 'nlp_search/nlpsearch_basic';
                    $form['#attached']['drupalSettings']['nlp_search']['entities'] = $entities['result'];
                    $form['#attached']['drupalSettings']['nlp_search']['path'] = drupal_get_path('module', 'nlp_search');
                    $form['#attached']['drupalSettings']['nlp_search']['entities_caption'] = '- ' . t('all entities') . ' -';
                    $form['#attached']['drupalSettings']['nlp_search']['rel_caption'] = '- ' . t('all relationships') . ' -';

                    //Das versteckte Feld vom Javascript beim Betätigen des Submit-Buttons mit dem Inhalt der Auswahlfelder
                    //für die Filtersuche befüllt.
                    $form['nlp_filter'] = array(
                        '#type' => 'hidden',
                        '#attributes' => array('id' => array('nlp-filter')),
                    );

                    $form['actions'] = [
                        '#type' => 'actions',
                    ];

                    $form['actions']['add_entity_btn'] = array(
                        '#type' => 'button',
                        '#value' => $this->t("Add Entity"),
                        '#attributes' => array('id' => array('nlpsearch-add-entity')),
                    );

                    $form['actions']['add_relationship_btn'] = array(
                        '#type' => 'button',
                        '#value' => $this->t("Add Relationship"),
                        '#attributes' => array('id' => array('nlpsearch-add-relationship')),
                    );

                    $form['actions']['lb'] = [
                        '#markup' => '<br><br>'
                    ];

                    $form['actions']['submit'] = [
                        '#type' => 'submit',
                        '#value' => $this->t('Search'),
                        '#attributes' => array('style' => array('margin-left: 0px;'))
                    ];

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

    public function validateForm(array &$form, FormStateInterface $form_state) {

    }

    public function submitForm(array &$form, FormStateInterface $form_state) {

        $nlp_fulltext = $form_state->getValue('nlp_fulltext');
        $nlp_filter = $form_state->getValue('nlp_filter');
        $nlp_filter_arr = json_decode($nlp_filter, true);

        global $base_url;

        //Wenn weder die Volltextsuche, noch die Filtersuche Inhalt haben, eine entsprechende Fehlermeldung anzeigen.
        if (empty($nlp_fulltext) && count($nlp_filter_arr['types']) == 0 && count($nlp_filter_arr['relationships']) == 0) {
            \Drupal::messenger()->addMessage(t('Nothing to search for'), 'error');
        } else {

            //Wenn für die Volltextsuche Inhalt definiert ist, soll vorrangig diese verwendet werden. Andernfalls wird
            //die Filtersuche angewendet.
            if (!empty($nlp_fulltext)) {

                //Eingebenen Suchquery an den Controller weiterleiten.
                $path = $base_url . '/nlp-search/results/fulltext/' . urlencode($nlp_fulltext);
                $response = new RedirectResponse($path, 302);
                $response->send();
                return;
            } else {
                if (isset($nlp_filter)) {

                    if (count($nlp_filter_arr['types']) > 0 || count($nlp_filter_arr['relationships']) > 0) {

                        //Eingegebene Suchfilter an den Controller weiterleiten.
                        $path = $base_url . '/nlp-search/results/filter/' . urlencode($nlp_filter);
                        $response = new RedirectResponse($path, 302);
                        $response->send();
                        return;
                    } else {
                        \Drupal::messenger()->addMessage(t('Nothing to search for'), 'error');
                    }
                }
            }
        }

        //
    }
}