'''
Created on 18.05.2019

@author: Corin
'''

import requests
import sys

class StanfordConnect(object):
    '''
    classdocs
    '''

    # Beim Initialisieren der Klasse werden URL und Port gesetzt
    def __init__(self, path_or_host, port=None):
        self.url = path_or_host + ':' + str(port)
        self.port = port

    # Die Funktion schickt einen Text, sowie ein Array mit Optionen an eine Instanz vom Stanford CoreNLP Servers und gibt das Ergebnis zurück.
    def annotate(self, text, properties=None):
        if sys.version_info.major >= 3:
            text = text.encode('utf-8')

        r = requests.post(self.url, timeout=120, params={'properties': str(properties)}, data=text,
                          headers={'Connection': 'close'},)
        return r.text