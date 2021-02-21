<?php

namespace Drupal\nlp_search\Controller;

use Drupal\Core\Controller\ControllerBase;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;

class AutocompleteController extends ControllerBase {
    public function handleAutocomplete(Request $request) {
        $available_entities = [
            'PERSON',
            'DATE',
            'CITY',
            'COUNTRY',
            'NATIONALITY',
            'LOCATION',
            'TITLE',
            'MISC',
            'RELIGION',
            'NUMBER',
            'ORDINAL',
            'DURATION',
            'ORGANIZATION',
            'IDEOLOGY',
            'STATE_OR_PROVINCE',
            'CAUSE_OF_DEATH',
            'SET',
            'TIME',
            'CRIMINAL_CHARGE' 
        ];

        return new JsonResponse($available_entities);
    }
}