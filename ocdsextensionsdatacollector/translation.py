import os
import json
import gettext
from collections import OrderedDict
from docutils.utils import new_document
from recommonmark.parser import CommonMarkParser

from ocdsdocumentationsupport.translation import translate_codelists, translate_schema # noqa

from ocdsextensionsdatacollector.markdown_translator import MarkdownTranslator


def translate_extension(domain, sourcedir, builddir, localedir, language):
    translator = gettext.translation(domain, localedir, languages=[language], fallback=language == 'en')

    os.makedirs(builddir, exist_ok=True)

    with open(os.path.join(sourcedir, 'extension.json')) as r, open(os.path.join(builddir, 'extension.json'), 'w') as w: # noqa
        data = json.load(r, object_pairs_hook=OrderedDict)
        for key in ('name', 'description'):
            if isinstance(data[key], dict):
                value = data[key]['en']
            else:
                value = data[key]
            new_value = translator.gettext(value)
            data[key] = {language: new_value}
        json.dump(data, w, indent=2, separators=(',', ': '), ensure_ascii=False)


def translate_docs(domain, source_dir, build_dir, locale_path, language, extension, version):
    parser = CommonMarkParser()
    document = new_document('{}/{}'.format(extension, version))
    visitor = MarkdownTranslator(document, domain, localedir=locale_path, language=language)
    with open(os.path.join(source_dir, 'README.md')) as f:
        english_readme = f.read()
    parser.parse(english_readme, document)
    document.walkabout(visitor)
    with open(os.path.join(build_dir, 'README.md'), 'w+') as f:
        f.write(visitor.astext())
