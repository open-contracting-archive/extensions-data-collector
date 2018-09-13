import json
from ocdsdocumentationsupport.babel_extractors import extract_codelist, extract_schema


TRANSLATABLE_EXTENSION_KEYWORDS = ('name', 'description')

def extract_extension_meta(fileobj, keywords, comment_tags, options):
    """
    Yields the "title" and "description" values of an extension.json file.
    """
    def gather_text(data, pointer=''):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    value = value.strip()
                elif isinstance(value, dict):
                    en_value = value.get('en')
                    if en_value:
                        value = en_value.strip()

                if key in TRANSLATABLE_EXTENSION_KEYWORDS and value:
                    yield value, '{}/{}'.format(pointer, key)

    data = json.loads(fileobj.read().decode())
    for text, pointer in gather_text(data):
        # yield lineno, funcname, message, comments
        yield 1, '', text, [pointer]