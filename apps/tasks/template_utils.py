"""
Utility functions for TaskTemplate feature.
"""


def render_extra_fields_to_description(
    extra_fields: list,
    form_data: dict,
) -> str:
    """
    Wandelt ausgefüllte Zusatzfelder in einen Markdown-formatierten
    Beschreibungsblock um.

    extra_fields: Liste der Feld-Definitionen aus TaskTemplate.get_extra_fields()
    form_data:    POST-Daten des Formulars (request.POST)

    Gibt einen Markdown-String zurück, z.B.:
    ## Briefing

    **Zielgruppe:** Studierende B.Sc. Informatik
    **Zeichenanzahl:** 800
    **Ton:** Informell
    **Besonderheiten:** Bitte kurze Absätze
    """
    if not extra_fields:
        return ''

    lines = ['## Briefing\n']

    for field in extra_fields:
        name  = field.get('name', '')
        label = field.get('label', name)
        ftype = field.get('type', 'text')
        value = form_data.get(f'extra_{name}', '')

        if ftype == 'multiselect':
            # Mehrfachauswahl: Liste aus POST
            values = form_data.getlist(f'extra_{name}')
            value  = ', '.join(values) if values else ''

        elif ftype == 'checkbox':
            value = 'Ja' if value else 'Nein'

        elif ftype == 'date' and value:
            # Datum in deutsches Format umwandeln
            try:
                from datetime import datetime
                d = datetime.strptime(value, '%Y-%m-%d')
                value = d.strftime('%d.%m.%Y')
            except ValueError:
                pass

        if value:
            lines.append(f'**{label}:** {value}')

    return '\n'.join(lines)


def validate_extra_fields(
    extra_fields: list,
    form_data: dict,
) -> list:
    """
    Validiert die Pflichtfelder.
    Gibt eine Liste von Fehlermeldungen zurück (leer = alles ok).
    """
    errors = []
    for field in extra_fields:
        name     = field.get('name', '')
        label    = field.get('label', name)
        required = field.get('required', False)
        ftype    = field.get('type', 'text')

        if not required:
            continue

        if ftype == 'multiselect':
            values = form_data.getlist(f'extra_{name}')
            if not values:
                errors.append(f'"{label}" ist ein Pflichtfeld.')
        else:
            value = form_data.get(f'extra_{name}', '').strip()
            if not value:
                errors.append(f'"{label}" ist ein Pflichtfeld.')

    return errors
