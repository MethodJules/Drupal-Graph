<?php
/**
 * Created by PhpStorm.
 * User: Corin
 * Date: 30.05.2019
 * Time: 16:47
 */

namespace Drupal\nlp_search\Controller;


use Drupal\Core\Access\AccessResult;
use Drupal\Core\Session\AccountInterface;
use Drupal\Core\Controller\ControllerBase;
use Drupal\node\Entity\Node;

class CheckAccessController extends ControllerBase {


    //Für Tabs Entitäten editieren und Entitäten hinzufügen soll überprüft werden, ob der Content Type der Node zu den
    //Content Types passt, die im Adminbereich zu dem Modul definiert wurden. Falls nicht, sollen die Tabs auch nicht
    // angezeigt werden.
    public function checkAccess($node) {
        $actualNode = Node::load($node);

        $config = \Drupal::config('nlp_search.settings');
        $saved_content_types = json_decode($config->get('nlp_search_content_types'), true);

        $node_bundle = array();
        foreach ($saved_content_types as $setting) {
            if (!in_array($setting['content_type'], $node_bundle)) {
                $node_bundle[] = $setting['content_type'];
            }
        }

        return AccessResult::allowedIf(in_array($actualNode->bundle(), $node_bundle));
    }
}