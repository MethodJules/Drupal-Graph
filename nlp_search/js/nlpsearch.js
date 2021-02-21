
(function ($) {
    $(document).ready(function () {

        var entities = drupalSettings.nlp_search.entities;

        //Wenn der Button gedrückt wird, ein neues Auswahlfeld erstellen und der Box hinzufügen.
        $(document).on('click', '#nlpsearch-add-entity', function(e) {
            e.preventDefault();
            var ent_select = '<select class="entity-select">';

            ent_select += '<option value="default" selected>' + drupalSettings.nlp_search.entities_caption + '</option>';
            for (var i = 0; i < Object.keys(entities['types']).length; i++) {
                ent_select += '<option value="' + Object.keys(entities['types'])[i] + '">' + Object.keys(entities['types'])[i] + '</option>';
            }

            ent_select += '</select>';

            var remove_btn = '<button class="entity-remove"></button>'
            $('#nlpsearch-filter-box').prepend('<div class="nlp-entity">' + ent_select + remove_btn + '</div>')
        });

        //Auswahlfeld entfernen, wenn auf das Symbol dafür geklickt wird.
        $(document).on('click', '.entity-remove', function() {
            $(this).parent().remove();
        });

        //Wird eine Entität ausgewählt, soll der Anwender noch festlegen können, um welche Entität es sich explizit handelt.
        $(document).on('change', '.entity-select, .entity-rel-select', function() {
            $(this).parent().find('.entity-detail-select').remove();

            //Überprüfen, ob der Wert nicht mehr default ist, sich also geändert hat.
            if ($(this).val() !== 'default') {

                var entity = $(this).val();
                var ent_select = '<select class="entity-detail-select">';

                //Von dem ausgewählten Typ der Entität, die genauen Bezeichnungen zu diesem Typ aus dem Array auslesen.
                ent_select += '<option value="default" selected>- all ' + entity + ' -</option>';
                for (var i = 0; i < entities['types'][entity].length; i++) {
                    ent_select += '<option value="' + entities['types'][entity][i] + '">' + entities['types'][entity][i] + '</option>';
                }

                ent_select += '</select>';

                $(this).after(ent_select);
            }
        });

        //Analog zum Hinzufügen von Entitäten, wenn zwischen zwei Entitäten auch noch eine Relation ausgewählt werden soll.
        $(document).on('click', '#nlpsearch-add-relationship', function(e) {
            e.preventDefault();
            var ent_select = '<select class="entity-select">';

            ent_select += '<option value="default" selected>' + drupalSettings.nlp_search.entities_caption + '</option>';
            for (var i = 0; i < Object.keys(entities['types']).length; i++) {
                ent_select += '<option value="' + Object.keys(entities['types'])[i] + '">' + Object.keys(entities['types'])[i] + '</option>';
            }

            ent_select += '</select>';

            var rel_select = '<select class="rel-select">';
            rel_select += '<option value="default" selected>' + drupalSettings.nlp_search.rel_caption + '</option>';

            for (var i = 0; i < entities['relationships'].length; i++) {
                rel_select += '<option value="' + entities['relationships'][i] + '">' + entities['relationships'][i] + '</option>';
            }

            rel_select += '</select>';

            var remove_btn = '<button class="entity-remove"></button>';
            var arrow_left = '<img class="arrow-sep" src="' + drupalSettings.nlp_search.path + '/css/arrow-left.png">';
            var arrow_right = '<img class="arrow-sep" src="' + drupalSettings.nlp_search.path +'/css/arrow-right.png">';
            var ent_rel = '<div class="left-box">' + ent_select + '</div>' + arrow_right + rel_select + arrow_left + '<div class="right-box">' + ent_select + "</div>" + remove_btn;

            $('#nlpsearch-filter-box').prepend('<div class="nlp-rel-entity">' + ent_rel + '</div>')
        });

        //Beim Abschicken des Buttons "Search" die Auswahlfelder iterieren, die gesetzten Werte auslesen
        $(document).on('click', '#edit-submit', function(e) {
            //e.preventDefault();
            var result = {};
            result['types'] = {};
            var ent_counter = 0;

            //Alle Auswahlfelder nur für Entitäten iterieren und die Werte auslesen.
            $('.nlp-entity').each(function() {
                var ner = $(this).find('.entity-select').val();
                var ner_text = $(this).find('.entity-detail-select').val();

                if (ner_text === undefined) {
                    ner_text = "default";
                }
                result['types'][ent_counter] = {};
                result['types'][ent_counter]['ner'] = ner;
                result['types'][ent_counter]['text'] = ner_text;

                ent_counter++;
            });

            var rel_counter = 0;

            result['relationships'] = {};

            //Alle Auswahlfelder für Entitäten und Relationen iterieren und die Werte auslesen
            $('.nlp-rel-entity').each(function() {
                var ner1 = $(this).find('.left-box').find('.entity-select').val();
                var ner1_text = $(this).find('.left-box').find('.entity-detail-select').val();

                var ner2 = $(this).find('.right-box').find('.entity-select').val();
                var ner2_text = $(this).find('.right-box').find('.entity-detail-select').val();

                var rel = $(this).find('.rel-select').val();

                if (ner1_text === undefined) {
                    ner1_text = "default";
                }

                if (ner2_text === undefined) {
                    ner2_text = "default";
                }
                result['relationships'][rel_counter] = {};
                result['relationships'][rel_counter]['ner1'] = ner1;
                result['relationships'][rel_counter]['ner1_text'] = ner1_text;
                result['relationships'][rel_counter]['ner2'] = ner2;
                result['relationships'][rel_counter]['ner2_text'] = ner2_text;
                result['relationships'][rel_counter]['rel'] = rel;


                rel_counter++;
            });

            //Zuletzt dem hidden Feld den Wert als Json zuweisen.
            $('#nlp-filter').val(JSON.stringify(result));
        });
    });
})(jQuery);