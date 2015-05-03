import re
import os
import io
import urllib
from wx import GetTranslation as _
try:
    from html import escape  # py3
except ImportError:
    from cgi import escape  # py2

#  http://abcnotation.com/wiki/abc:standard:v2.1#information_field_definition
# keyword | name |file header | tune header | tune body | inline | type | examples and notes
abc_keywords = """\
A:|area              |yes    |yes    |no     |no     |string      |A:Donegal, A:Bampton (deprecated)
B:|book              |yes    |yes    |no     |no     |string      |B:O'Neills
C:|composer          |yes    |yes    |no     |no     |string      |C:Robert Jones, C:Trad.
D:|discography       |yes    |yes    |no     |no     |string      |D:Chieftains IV
F:|file url          |yes    |yes    |no     |no     |string      |F:http://a.b.c/file.abc
G:|group             |yes    |yes    |no     |no     |string      |G:flute
H:|history           |yes    |yes    |no     |no     |string      |H:The story behind this tune
I:|instruction       |yes    |yes    |yes    |yes    |instruction |I:papersize A4, I:newpage
K:|key               |no     |last   |yes    |yes    |instruction |K:G, K:Dm, K:AMix
L:|unit note length  |yes    |yes    |yes    |yes    |instruction |L:1/4, L:1/8
M:|meter             |yes    |yes    |yes    |yes    |instruction |M:3/4, M:4/4
m:|macro             |yes    |yes    |yes    |yes    |instruction |m: ~G2 = {A}G{F}G
N:|notes             |yes    |yes    |yes    |yes    |string      |N:see also O'Neills - 234
O:|origin            |yes    |yes    |no     |no     |string      |O:UK; Yorkshire; Bradford
P:|parts             |no     |yes    |yes    |yes    |instruction |P:A, P:ABAC, P:(A2B)3
Q:|tempo             |no     |yes    |yes    |yes    |instruction |Q:"allegro" 1/4=120
R:|rhythm            |yes    |yes    |yes    |yes    |string      |R:R, R:reel
r:|remark            |yes    |yes    |yes    |yes    |string      |r:I love abc
S:|source            |yes    |yes    |no     |no     |string      |S:collected in Brittany
s:|symbol line       |no     |no     |yes    |no     |instruction |s: !pp! ** !f!
T:|tune title        |no     |second |yes    |no     |string      |T:Paddy O'Rafferty
U:|user defined      |yes    |yes    |yes    |yes    |instruction |U: T = !trill!
V:|voice             |no     |yes    |yes    |yes    |instruction |V:4 clef=bass
W:|words             |no     |yes    |yes    |no     |string      |W:lyrics printed after the end of the tune
w:|words             |no     |no     |yes    |no     |string      |w:lyrics printed aligned with the notes of a tune
X:|reference number  |no     |first  |no     |no     |instruction |X:1, X:2
Z:|transcription     |yes    |yes    |no     |no     |string      |Z:John Smith, <j.s@mail.com>
"""

name_to_display_text = {
    'staves' : _('Staff layout'),
}

decorations = {
    '.'                : _('staccato mark'),
    '~'                : _('Irish roll'),
    'H'                : _('fermata'),
    'L'                : _('accent or emphasis'),
    'M'                : _('lowermordent'),
    'O'                : _('coda'),
    'P'                : _('uppermordent'),
    'S'                : _('segno'),
    'T'                : _('trill'),
    'u'                : _('up-bow'),
    'v'                : _('down-bow'),
    '!trill!'          : _('"tr" (trill mark)'),
    '!trill(!'         : _('start of an extended trill'),
    '!trill)!'         : _('end of an extended trill'),
    '!lowermordent!'   : _('short /|/|/ squiggle with a vertical line through it'),
    '!uppermordent!'   : _('short /|/|/ squiggle'),
    '!mordent!'        : _('short /|/|/ squiggle with a vertical line through it'),
    '!pralltriller!'   : _('short /|/|/ squiggle'),
    '!roll!'           : _('a roll mark (arc) as used in Irish music'),
    '!turn!'           : _('a turn mark (also known as gruppetto)'),
    '!turnx!'          : _('a turn mark with a line through it'),
    '!invertedturn!'   : _('an inverted turn mark'),
    '!invertedturnx!'  : _('an inverted turn mark with a line through it'),
    '!arpeggio!'       : _('vertical squiggle'),
    '!>!'              : _('> mark'),
    '!accent!'         : _('> mark'),
    '!emphasis!'       : _('> mark'),
    '!fermata!'        : _('fermata or hold (arc above dot)'),
    '!invertedfermata!': _('upside down fermata'),
    '!tenuto!'         : _('horizontal line to indicate holding note for full duration'),
    '!0!'              : _('fingering (none)'),
    '!1!'              : _('fingering (thumb)'),
    '!2!'              : _('fingering (index finger)'),
    '!3!'              : _('fingering (middle finger)'),
    '!4!'              : _('fingering (ring finger)'),
    '!5!'              : _('fingering (pinky)'),
    '!+!'              : _('left-hand pizzicato, or rasp for French horns'),
    '!plus!'           : _('left-hand pizzicato, or rasp for French horns'),
    '!snap!'           : _('snap-pizzicato mark, visually similar to !thumb!'),
    '!slide!'          : _('slide up to a note, visually similar to a half slur'),
    '!wedge!'          : _('small filled-in wedge mark'),
    '!upbow!'          : _('V mark'),
    '!downbow!'        : _('squared n mark'),
    '!open!'           : _('small circle above note indicating open string or harmonic'),
    '!thumb!'          : _('cello thumb symbol'),
    '!breath!'         : _('a breath mark (apostrophe-like) after note'),
    '!pppp!'           : _('pianissimo possibile'),
    '!ppp!'            : _('pianississimo'),
    '!pp!'             : _('pianissimo'),
    '!p!'              : _('piano'),
    '!mp!'             : _('mezzopiano'),
    '!mf!'             : _('mezzoforte'),
    '!f!'              : _('forte'),
    '!ff!'             : _('fortissimo'),
    '!fff!'            : _('fortississimo'),
    '!ffff!'           : _('fortissimo possibile'),
    '!sfz!'            : _('sforzando'),
    '!crescendo(!'     : _('start of a < crescendo mark'),
    '!<(!'             : _('start of a < crescendo mark'),
    '!crescendo)!'     : _('end of a < crescendo mark, placed after the last note'),
    '!<)!'             : _('end of a < crescendo mark, placed after the last note'),
    '!diminuendo(!'    : _('start of a > diminuendo mark'),
    '!>(!'             : _('start of a > diminuendo mark'),
    '!diminuendo)!'    : _('end of a > diminuendo mark, placed after the last note'),
    '!>)!'             : _('end of a > diminuendo mark, placed after the last note'),
    '!segno!'          : _('2 ornate s-like symbols separated by a diagonal line'),
    '!coda!'           : _('a ring with a cross in it'),
    '!D.S.!'           : _('the letters D.S. (=Da Segno)'),
    '!D.C.!'           : _('the letters D.C. (=either Da Coda or Da Capo)'),
    '!dacoda!'         : _('the word "Da" followed by a Coda sign'),
    '!dacapo!'         : _('the words "Da Capo"'),
    '!fine!'           : _('the word "fine"'),
    '!shortphrase!'    : _('vertical line on the upper part of the staff'),
    '!mediumphrase!'   : _('vertical line on the upper part of the staff, extending down to the centre line'),
    '!longphrase!'     : _('vertical line on the upper part of the staff, extending 3/4 of the way down')
}


ABC_TUNE_HEADER_NO = 0
ABC_TUNE_HEADER_FIRST = 1
ABC_TUNE_HEADER_SECOND = 2
ABC_TUNE_HEADER_YES = 3
ABC_TUNE_HEADER_LAST = 4
tune_header_lookup = {'no': ABC_TUNE_HEADER_NO, 'first': ABC_TUNE_HEADER_FIRST, 'second': ABC_TUNE_HEADER_SECOND, 'yes': ABC_TUNE_HEADER_YES, 'last': ABC_TUNE_HEADER_LAST}

ABC_SECTION_FILE_HEADER = 0
ABC_SECTION_TUNE_HEADER = 1
ABC_SECTION_TUNE_BODY = 2
ABC_SECTIONS = [
    ABC_SECTION_FILE_HEADER,
    ABC_SECTION_TUNE_HEADER,
    ABC_SECTION_TUNE_BODY
]


def replace_text(text, replacements):
    """
    Args:
        text: text that requires replacements
        replacements: A sequence of tuples in the form (compiled regular expression object, replacement value)

    Returns:
        the original text with all replacements applied
    """
    for regex, replace_value in replacements:
        text = regex.sub(replace_value, text)
    return text

def remove_named_groups(pattern):
    return re.sub(r'(?<=\(\?)P\<[^\>]+\>', ':', pattern)

class AbcElement(object):
    def __init__(self, name, keyword=None, group_name=None, display_name=None, description=None, validation_pattern=None):
        self.name = name
        self.group_name = group_name
        self.keyword = keyword
        if display_name is None:
            self.__display_name = name_to_display_text.get(name, _(name[:1].upper() + name[1:]))
        else:
            self.__display_name = display_name
        self.description = description
        self.mandatory = False
        self.default = None
        self.rest_of_line_pattern = r'(.*?)(?:(?<!\\)%.*)?$'
        self._search_pattern = {}
        self._search_re = {} # compiled regex
        self.params = []
        self.validation_pattern = validation_pattern
        self.__validation_re = None
        self.supported_values = None
        self.exact_match_required = False

        #self.html_cache_name = os.path.join(cache_path, "".join([x if x.isalnum() else "_" for x in name]))

    @staticmethod
    def get_inline_pattern(keyword):
        return r'\[' + re.escape(keyword) + r'([^\]\n\r]*)\]'

    def freeze(self):
        for section in ABC_SECTIONS:
            pattern = self._search_pattern.get(section, None)
            if pattern is not None:
                self._search_re[section] = re.compile(pattern)

        if self.validation_pattern is not None:
            self.__validation_re = re.compile(self.validation_pattern)

    def matches(self, context):
        regex = self._search_re.get(context.abc_section, None)
        if regex is not None:
            if self.exact_match_required:
                text = context.selected_text
            else:
                text = context.lines
            p1, p2 = context.selection
            if p1 == p2 or (0 <= p1 < len(text) and text[p1] in ' \r\n\t'):
                for m in regex.finditer(text):
                    if m.start() <= context.selection[0] <= context.selection[1] <= m.end():
                        return m
            else:
                if p1 > len(text):
                    print 'Selection past length: %d %d %s' % (p1, len(text), text)
                for m in regex.finditer(text):
                    if m.start() <= context.selection[0] <= context.selection[1] < m.end():
                        return m
        return None

    def matches_text(self, context, text):
        regex = self._search_re.get(context.abc_section, None)
        if regex is not None:
            return regex.search(text)
        return None

    def replace_text(self, context, text, replace_value):
        return self._search_re[context.abc_section].sub(replace_value, text)

    @property
    def display_name(self):
        return self.__display_name

    @property
    def validation_regex(self):
        return self.__validation_regex

    def get_description_url(self, context):
        return None

    @staticmethod
    def get_html_from_url(url):
        result = u''
        try:
            result = urllib2.urlopen(url).read()
        except urllib2.HTTPError as ex:
            pass
        except urllib2.URLError as ex:
            pass
        return result

    def get_header_text(self, context):
        return self.__display_name

    def get_description_text(self, context):
        return self.description

    def get_description_html(self, context):
        result = None
        url = self.get_description_url(context)
        if url:
            result = self.get_html_from_url(url)
        if not result:
            result = u'<h3>%s</h3>' % escape(self.get_header_text(context))
            description = self.get_description_text(context)
            if description:
                result += escape(description) + '<br>'

            groups = context.current_match.groups()
            element_text = context.match_text
            if len(groups) == 1 and groups[0]:
                element_text = groups[0]

            result += '<code>%s</code><br>' % escape(element_text)
            #for matchtext in context.current_match.groups():
            #    if matchtext:
            #        result += '<code>%s</code><br>' % escape(matchtext)
        return result


class CompositeElement(AbcElement):
    def __init__(self, name, keyword=None, group_name=None, display_name=None, description=None):
        super(CompositeElement, self).__init__(name, keyword, group_name, display_name, description)
        self._elements = {}

    def add_element(self, element):
        if element.keyword:
            self._elements[element.keyword] = element
        else:
            raise Exception('Element has no keyword')

    def get_element(self, keyword):
        return self._elements.get(keyword)

    def get_element_from_context(self, context):
        inner_text = context.current_match.group(1)
        if inner_text is None:
            inner_text = context.current_match.group(2)
        keyword = inner_text.split(' ', 1)[0]
        return self._elements.get(keyword)

    def get_header_text(self, context):
        element = self.get_element_from_context(context)
        if element:
            return element.get_header_text(context)
        return super(CompositeElement, self).get_header_text(context)

    def get_description_text(self, context):
        element = self.get_element_from_context(context)
        if element:
            return element.get_description_text(context)
        return super(CompositeElement, self).get_description_text(context)


class AbcUnknown(AbcElement):
    pattern = ''
    def __init__(self):
        super(AbcUnknown, self).__init__('Unknown')
        for section in ABC_SECTIONS:
            self._search_pattern[section] = AbcUnknown.pattern


class AbcInformationField(AbcElement):
    def __init__(self, keyword, name, file_header, tune_header, tune_body, inline, examples):
        super(AbcInformationField, self).__init__(name, keyword, group_name='ABC information')
        self.file_header = file_header
        self.tune_header = tune_header
        self.tune_body = tune_body
        self.inline = inline
        self.examples = examples

        line_pattern = r'(?m)^' + re.escape(self.keyword) + self.rest_of_line_pattern
        if file_header:
            self._search_pattern[ABC_SECTION_FILE_HEADER] = line_pattern
        if tune_header in [ABC_TUNE_HEADER_YES, ABC_TUNE_HEADER_FIRST, ABC_TUNE_HEADER_SECOND, ABC_TUNE_HEADER_LAST]:
            self._search_pattern[ABC_SECTION_TUNE_HEADER] = line_pattern
        if tune_body or inline:
            pattern = line_pattern
            if inline:
                pattern += '|' + self.get_inline_pattern(keyword)
            self._search_pattern[ABC_SECTION_TUNE_BODY] = pattern


class AbcDirective(CompositeElement):
    def __init__(self):
        super(AbcDirective, self).__init__('stylesheet directive', group_name='stylesheet directive', description=_('A stylesheet directive is a line that starts with %%, followed by a directive that gives instructions to typesetting or player programs.'))
        pattern = r'(?m)^(?:%%|I:)(?!%)' + self.rest_of_line_pattern + '|' + self.get_inline_pattern('I:')
        for section in ABC_SECTIONS:
            self._search_pattern[section] = pattern


class AbcStringField(AbcInformationField):
    def __init__(self, keyword, name, file_header, tune_header, tune_body, inline, examples):
        super(AbcStringField, self).__init__(name, keyword, file_header, tune_header, tune_body, inline, examples)


class AbcInstructionField(AbcInformationField):
    def __init__(self, keyword, name, file_header, tune_header, tune_body, inline, examples):
        super(AbcInstructionField, self).__init__(name, keyword, file_header, tune_header, tune_body, inline, examples)


class AbcMidiDirective(CompositeElement):
    def __init__(self):
        super(AbcMidiDirective, self).__init__('MIDI directive', 'MIDI', group_name='MIDI', description=_('A directive that gives instructions to player programs.'))
        # pattern = re.escape('<a name="%s"></a>' % name) + '(.*?)' + re.escape('<a name=')
        # self.html_re = re.compile(pattern, re.MULTILINE or re.IGNORECASE)

    # def get_description_url(self):
    #     return 'http://ifdo.pugmarks.com/~seymour/runabc/abcguide/abc2midi_body.html#%s' % urllib.quote(self.name)

    # def get_description_html(self, context):
    #     html = super(AbcMidiDirective, self).get_description_html(context)
    #     m = self.html_re.search(html)
    #     if m:
    #         html = m.groups(1)
    #     return html


class Abcm2psDirective(AbcElement):
    """ Elements defined by abcm2ps """
    anchor_replacement = (re.compile('<a (?:href|name)="[^"]*">|</a>', re.IGNORECASE), '')
    table_replacement = (re.compile('<table>.*?</table>', re.IGNORECASE | re.DOTALL), '')

    # r''
    # <table border="1">
    # <tr align="center">
    # <td width="25%">Default</td>
    # <td width="25%">Command line</td><td width="25%">Scope</td>
    # <td width="25%">Available in</td>
    # </tr>
    # <tr align="center">
    # <td>false</td>
    # <td>trailing 'b'<br/>at end of <code>-j</code> or <code>-k</code></td>
    # <td>generation</td><td>abcm2ps<br/>abc2svg</td>
    # </tr>
    # </table>

    def __init__(self, keyword, name, description=None):
        super(Abcm2psDirective, self).__init__(keyword, name, group_name='abcm2ps', description=description)
        self.html_replacements = [
            Abcm2psDirective.anchor_replacement,
            Abcm2psDirective.table_replacement
        ]

    def get_description_url(self):
        return 'http://moinejf.free.fr/abcm2ps-doc/%s.xhtml' % urllib.quote(self.name)

    def get_html_from_url(self, url):
        result = super(Abcm2psDirective, self).get_html_from_url(url)
        result = replace_text(result, self.html_replacements)
        return result


class AbcComment(AbcElement):
    #pattern = r'(?<!\\|^)%\s*(.*)|^%(?!%)\s*(.*)$'
    pattern = r'(?<!\\)%\s*(.*)$'
    def __init__(self):
        super(AbcComment, self).__init__('Comment', '%')
        for section in ABC_SECTIONS:
            self._search_pattern[section] = AbcComment.pattern
        self._search_pattern[ABC_SECTION_TUNE_BODY] += '|`+'

    def get_header_text(self, context):
        if context.match_text.startswith('%%'):
            return _('Stylesheet directive')
        else:
            return super(AbcComment, self).get_header_text(context)

    def get_description_text(self, context):
        if context.match_text.startswith('%%'):
            return _('A stylesheet directive is a line that starts with %%, followed by a directive that gives instructions to typesetting or player programs.')
        else:
            return super(AbcComment, self).get_description_text(context)

    def remove_comments(self, abc):
        return self._search_re[ABC_SECTION_TUNE_BODY].sub('', abc)


class AbcEmptyLine(AbcElement):
    pattern = r'^\s*$'
    def __init__(self):
        super(AbcEmptyLine, self).__init__('Empty line', description=_('An empty line is waiting to be filled. It is also a tune separator.'))
        for section in ABC_SECTIONS:
            self._search_pattern[section] = AbcEmptyLine.pattern


class AbcBodyElement(AbcElement):
    def __init__(self, name, pattern, description=None):
        super(AbcBodyElement, self).__init__(name, group_name='Music code', description=description)
        self._search_pattern[ABC_SECTION_TUNE_BODY] = pattern
        self.pattern = pattern


class AbcSpace(AbcBodyElement):
    pattern = r'\s+'
    def __init__(self):
        super(AbcSpace, self).__init__('Whitespace', AbcSpace.pattern)


class AbcChordSymbol(AbcBodyElement):
    pattern = r'"[^\^_<>@]((?:\\"|[^"])*)"'
    def __init__(self):
        super(AbcChordSymbol, self).__init__('Chord', AbcChordSymbol.pattern, description=_('Chord'))


class AbcAnnotation(AbcBodyElement):
    pattern = r'"(?P<pos>[\^_<>@])((?:\\"|[^"])*)"'
    def __init__(self):
        super(AbcAnnotation, self).__init__('Annotation', AbcAnnotation.pattern, description=_('An annotation'))


class AbcSlur(AbcBodyElement):
    pattern = r'\((?!\d)|\)'
    def __init__(self):
        super(AbcSlur, self).__init__('Slur', AbcSlur.pattern)


class AbcGrace(AbcBodyElement):
    pattern = '{/?|}'
    def __init__(self):
        super(AbcGrace, self).__init__('Grace notes', AbcGrace.pattern, description=_('Grace notes can be written by enclosing them in curly braces. To distinguish between appoggiaturas and acciaccaturas, the latter are notated with a forward slash immediately following the open brace.'))


class AbcChordBeginAndEnd(AbcBodyElement):
    pattern = r'\[|\]'
    def __init__(self):
        super(AbcChordBeginAndEnd, self).__init__('Chord', AbcChordBeginAndEnd.pattern, description=_('Multiple simultaneous notes.'))


class TypesettingSpace(AbcBodyElement):
    pattern = 'y'
    def __init__(self):
        super(TypesettingSpace, self).__init__('Typesetting extra space', TypesettingSpace.pattern, description=_('y can be used to add extra space between the surrounding notes; moreover, chord symbols and decorations can be attached to it, to separate them from notes.'))


class RedefinableSymbol(AbcBodyElement):
    pattern = '[H-Wh-w~]'
    def __init__(self):
        super(RedefinableSymbol, self).__init__('Redefinable symbol', RedefinableSymbol.pattern, description=_('As a short cut to writing symbols which avoids the !symbol! syntax, the letters H-W and h-w and the symbol ~ can be assigned with the U: field. For example, to assign the letter T to represent the trill, you can write: U: T = !trill!'))


class AbcDecoration(AbcBodyElement):
    pattern = r"!([^!]+)!|\+([^!]+)\+|[\.~HLMOPSTuv]"
    def __init__(self):
        super(AbcDecoration, self).__init__('Decoration', AbcDecoration.pattern)

    def get_description_html(self, context):
        html = super(AbcDecoration, self).get_description_html(context)
        html += '<br>'
        symbol = context.match_text
        if symbol[0] == symbol[-1] == '+': # convert old notation to new
            symbol = '!%s!' % symbol[1:-1]
        html += decorations.get(symbol, _('Unknown symbol'))
        html += '<br>'
        return html


class AbcBrokenRhythm(AbcBodyElement):
    pattern = r'\<+|\>+'
    def __init__(self):
        super(AbcBrokenRhythm, self).__init__('Broken rhythm', AbcBrokenRhythm.pattern)

    def get_description_html(self, context):
        html = super(AbcBrokenRhythm, self).get_description_html(context)
        if '>' in context.match_text:
            html += 'The previous note is dotted, the next note halved'
        else: # if '<' in context.match_text:
            html += 'The previous note is halved, the next dotted'
        return html


class AbcTuplet(AbcBodyElement):
    pattern = r"\([1-9](?:\:[1-9]?)?(?:\:[1-9]?)?"
    def __init__(self):
        super(AbcTuplet, self).__init__('Tuplet', AbcTuplet.pattern, description=_('Duplets, triplets, quadruplets, etc.'))


class AbcBar(AbcBodyElement):
    pattern = r"\.?\|\||:*\|\]|\[\|:*|::|:+\||\|:+|\.?\||\[\|\]"
    def __init__(self):
        super(AbcBar, self).__init__('Bar', AbcBar.pattern, description=_('Separates measures.'))


class AbcVariantEnding(AbcBodyElement):
    pattern = r'\[[1-9](?:[,-][1-9])*|\|[1-9]'
    def __init__(self):
        super(AbcVariantEnding, self).__init__('Variant ending', AbcVariantEnding.pattern, description=_('To play a different ending each time'))


class AbcVoiceOverlay(AbcBodyElement):
    pattern = '&'
    def __init__(self):
        super(AbcVoiceOverlay, self).__init__('Voice overlay', AbcVoiceOverlay.pattern, description=_("The & operator may be used to temporarily overlay several voices within one measure. Each & operator sets the time point of the music back by one bar line, and the notes which follow it form a temporary voice in parallel with the preceding one. This may only be used to add one complete bar's worth of music for each &. "))


class AbcInvalidCharacter(AbcBodyElement):
    pattern = r'[^\d\w\s%s]' % re.escape('!"#$%&\'()*+,-./:;<=>?@[\]^_`{|}~')
    def __init__(self):
        super(AbcInvalidCharacter, self).__init__('Invalid character', AbcInvalidCharacter.pattern, description=_("This character is not allowed within the body of an abc tune."))


class AbcBaseNote(AbcBodyElement):
    accidental_pattern = r'(?P<accidental>(?:\^{1,2}|_{1,2}|=)?)'
    length_pattern = r'(?P<length>(?:[1-9/][0-9/]*)?)'
    octave_pattern = r"(?P<octave>[',]*)"
    pair_pattern = r'(?P<pair>(?:-| *[><])?)'
    note_pattern = r'{0}(?P<note>[A-Ga-g]){1}{2}'.format(accidental_pattern, octave_pattern, length_pattern)
    normal_rest_pattern = '[zx]{0}?'.format(length_pattern)
    note_or_rest_pattern = '(?:{0}|{1})'.format(note_pattern, normal_rest_pattern)
    measure_rest_pattern = '[ZX](?P<measures>(?:[1-9][0-9]*)?)'
    def __init__(self, name, pattern, description=None):
        super(AbcBaseNote, self).__init__(name, pattern, description=description)


class AbcNote(AbcBaseNote):
    pattern = AbcBaseNote.note_pattern
    def __init__(self):
        super(AbcNote, self).__init__('Note', AbcNote.pattern)


class AbcRest(AbcBaseNote):
    pattern = '(?:{0}|{1})'.format(AbcBaseNote.normal_rest_pattern, AbcBaseNote.measure_rest_pattern)
    def __init__(self):
        super(AbcBaseNote, self).__init__('Rest', AbcRest.pattern)

    def get_header_text(self, context):
        if context.match_text[0] in 'XZ':
            return _('Whole measure rest')
        else:
            return super(AbcComment, self).get_header_text(context)

    def get_description_html(self, context):
        html = super(AbcRest, self).get_description_html(context)

        if context.match_text[0] in 'Xx':
            html += '{0}'.format(_('Invisible'))
        return html


class AbcGraceNotes(AbcBaseNote):
    pattern = r'{/?([^}]*)}'
    def __init__(self):
        super(AbcBaseNote, self).__init__('Grace notes', AbcGraceNotes.pattern)


class AbcChord(AbcBaseNote):
    pattern = r'\[(?:{0}*{1})+\]'.format(AbcDecoration.pattern, AbcBaseNote.note_pattern)
    def __init__(self):
        super(AbcBaseNote, self).__init__('Chord', AbcChord.pattern)


class AbcNoteGroup(AbcBaseNote):
    pattern = r'{0}?{1}?(?:{2}|{3})*{4}{5}'.format(AbcGraceNotes.pattern, AbcChordSymbol.pattern, AbcDecoration.pattern,
                                               AbcAnnotation.pattern, AbcBaseNote.note_pattern, AbcBaseNote.pair_pattern)
    def __init__(self):
        super(AbcBaseNote, self).__init__('Note group', '^{0}$'.format(AbcNoteGroup.pattern))
        self.exact_match_required = True

class AbcMultipleNotes(AbcBaseNote):
    pattern = '(?:{0}|{1})(?:\s*(?:{0}|{1}))+'.format(remove_named_groups(AbcNoteGroup.pattern), remove_named_groups(AbcBaseNote.normal_rest_pattern))
    def __init__(self):
        super(AbcBaseNote, self).__init__('Multiple notes', '^{0}$'.format(AbcMultipleNotes.pattern))
        self.exact_match_required = True


class AbcStructure(object):
    # static variables
    replace_regexes = None
    valid_directive_re = None
    from_to_directive_re = None
    abc_field_re = None

    @staticmethod
    def get_sections(cwd):
        # [1.3.6.2 [JWDJ] bugfix This fixes 'str>ng' in Fields and Command Reference
        reference_content = io.open(os.path.join(cwd, 'reference.txt'), 'rU', encoding='latin-1').read()
        if AbcStructure.replace_regexes is None:
            AbcStructure.replace_regexes = [
                (re.compile(r'\bh((?:bass/chord|length|logical|string|int|fl-?\n?oat\s?|command|str|text|vol)\d*(?: (?:string|int|float)\d*)*)i\b'), r'<\1>'),  # enclose types with < and >
                (re.compile(r'\[((?:bass/chord|length|logical|string|int|float|command|str|text|vol)\d*)\]'), r'<\1>'),  # replace types enclosed [ and ] with < and >
                (re.compile(r'(?m)\b(?<![-\s])1\d\d[\s\n]+[A-Z]+[A-Z\s\.&]+$'), ''),  # strip left page header
                (re.compile(r'\bA\.\d+\.[\s\n]+[A-Z ]*1\d\d\b'), ''),  # strip right page header
                (re.compile(r'[\.,]\s[\w\n\s]+Section [1-9A-Z]\.\d+.\d+[\w\s]*\.'), '.'),  # removes references to sections
                (re.compile(r'(?m)^(\w:)\s+((?:[a-z]+\s(?:in|of)\s)?(?:header(?:,\s?body)?|body))\s+(.*)$'), r'\1 \3 (\2)'),  # places where-field at the end of description
                (re.compile(r'\bh(\d+-\d+)i\b'), '(\1)')  # fix midi numbers (0-127)
            ]
            AbcStructure.valid_directive_re = re.compile(r'^%%\w+(\s[^:\n]*|\.\.\.[^:\n]*)?:')  # 1.3.6.2 [JWDJ] 2015-03 fixes false positives
            AbcStructure.from_to_directive_re = re.compile(r'(%%\w+)\.\.\.(%%\w+)')
            AbcStructure.abc_field_re = re.compile(r'[A-Za-z]:')

        reference_content = replace_text(reference_content, AbcStructure.replace_regexes)

        lines = reference_content.splitlines()

        for i in range(len(lines)):
            lines[i] = lines[i].replace('hinti', '<int>')
            lines[i] = lines[i].replace('%%MIDI drumoff turns', '%%MIDI drumoff: turns')
            lines[i] = lines[i].replace('%%MIDI drumon turns', '%%MIDI drumon: turns')

        sections = []
        cur_section = []
        abc_fields_done = False
        for line in lines:
            line = line.rstrip()
            if line.startswith('A.'):
                title = line.split(' ', 1)[1]
                cur_section = []
                sections.append((title, cur_section))
            elif AbcStructure.valid_directive_re.search(line): # 1.3.6.2 [JWDJ] 2015-03 fixes false positives
                abc_fields_done = True
                cur_section.append(line)
            elif not abc_fields_done and AbcStructure.abc_field_re.match(line):
                cur_section.append(line)
            elif cur_section: # join two lines
                if cur_section[-1].endswith('-'):
                    cur_section[-1] = cur_section[-1][:-1] + line
                else:
                    cur_section[-1] = cur_section[-1] + ' ' + line

        for i in range(len(sections)):
            section_name, lines = sections[i]
            tuples = []
            for line in lines:
                if AbcStructure.abc_field_re.match(line):
                    name, desc = line.split(' ', 1)
                    tuples.append((name, desc))
                elif len(line.split(': ', 1)) == 2:
                    name, desc = tuple(line.split(': ', 1))
                    m = AbcStructure.from_to_directive_re.match(name)
                    if m:
                        tuples.append((m.group(1), desc))
                        tuples.append((m.group(2), desc))
                    else:
                        tuples.append((name, desc))

            sections[i] = section_name, tuples
        return sections


    @staticmethod
    def generate_abc_elements(cwd):
        directive = AbcDirective()
        midi_directive = AbcMidiDirective()
        directive.add_element(midi_directive)
        result = [
            AbcEmptyLine(),
            directive,
            AbcComment(),
        ]

        elements_by_keyword = {}
        lines = str.splitlines(abc_keywords)
        for line in lines:
            parts = line.split('|')
            keyword = parts[0].strip()
            name = parts[1].strip()
            file_header = parts[2].strip() == 'yes'
            tune_header = tune_header_lookup[parts[3].strip()]
            tune_body = parts[4].strip() == 'yes'
            inline = parts[5].strip() == 'yes'
            abc_type = parts[6].strip()
            examples = parts[7].strip()
            if abc_type == 'instruction':
                element = AbcInstructionField(name, keyword, file_header, tune_header, tune_body, inline, examples)
            elif abc_type == 'string':
                element = AbcStringField(name, keyword, file_header, tune_header, tune_body, inline, examples)
            else:
                raise Exception('Unknown abc-type')
            result.append(element)
            elements_by_keyword[element.keyword] = element

        for (title, fields) in AbcStructure.get_sections(cwd):
            for (field_name, description) in fields:
                parts = field_name.split('<', 1)
                keyword = parts[0].rstrip()
                name = keyword
                element_holder = None
                if name.startswith('%%'):
                    name = name[2:]
                    if name[0:4] == 'MIDI':
                        element_holder = midi_directive
                        name = name[5:]
                        keyword = name
                    else:
                        element_holder = directive

                if element_holder:
                    existing_element = element_holder.get_element(keyword)
                else:
                    existing_element = elements_by_keyword.get(keyword)

                if existing_element is not None:
                    element.description = description
                else:
                    if element_holder:
                        if element_holder ==  midi_directive:
                            element = AbcElement(field_name, name, description=description)
                            midi_directive.add_element(element)
                        else:
                            element = Abcm2psDirective(field_name, name, description=description)
                            directive.add_element(element)
                    else:
                        if len(name) == 2 and name[-1] == ':':
                            element = AbcElement(field_name, name, description=description)
                            elements_by_keyword[keyword] = element
                            result.append(element)

                    for part in parts[1:]:
                        param = part.strip()
                        if param[-1] == '>':
                            param = param[:-1]
                        element.params.append(param)

        # elements = sorted(elements, key=lambda element: -len(element.keyword))  # longest match first


        # midi guide
        # http://abc.sourceforge.net/abcMIDI/original/abcguide.txt

        measure_number_options = {'None': None, 'Start of every line': 0, 'Every measure': 1, 'Every 2 measures': 2, 'Every 3 measures': 3, 'Every 4 measures': 4, 'Every 5 measures': 5, 'Every 8 measures': 8, 'Every 10 measures': 10}

    #     elements = [
    #         Abcm2psElement('pagewidth', _('Page width'), 'unit'),
    #         Abcm2psElement('pageheight', _('Page height'), 'unit'),
    #         Abcm2psElement('topmargin', _('Top margin'), 'unit'),
    #         Abcm2psElement('botmargin', _('Bottom margin'), 'unit'),
    #         Abcm2psElement('leftmargin', _('Left margin'), 'unit'),
    #         Abcm2psElement('rightmargin', _('Right margin'), 'unit'),
    #         Abcm2psElement('staffwidth', _('Staff width'), 'unit'),
    #         Abcm2psElement('landscape', _('Landscape'), 'bool'),
    #         Abcm2psElement('scale', _('Page scale factor'), 'float'),
    #         Abcm2psElement('staffscale', _('Staff scale factor'), 'float'),
    #         Abcm2psElement('setbarnb', _('First measure number'), 'int'),
    #         Abcm2psElement('measurenb', _('Measure numbers'), 'int', measure_number_options),

        result += [
            AbcChordSymbol(),
            AbcAnnotation(),
            AbcTuplet(),
            AbcVariantEnding(),
            AbcBar(),
            AbcDecoration(),
            AbcSlur(),
            AbcNote(),
            AbcRest(),
            AbcGrace(),
            AbcChordBeginAndEnd(),
            AbcVoiceOverlay(),
            AbcBrokenRhythm(),
            AbcInvalidCharacter(),
            AbcChord(),
            AbcNoteGroup(),
            AbcMultipleNotes(),
            TypesettingSpace(),
            RedefinableSymbol(),
            AbcSpace(),
            AbcUnknown()
        ]

        for element in result:
            try:
                element.freeze()
            except Exception as e:
                print 'Exception in %s: %s    ->   %s' % (element.name, element.pattern,  e)

        return result

#def create_abc_elements():
#    index_element = AbcStructureElement('X:', _('Index'))
#    index_element.mandatory = True
#    title_element = AbcTextElement('T:', _('Title'), multiline=True)
#    title_element.mandatory = True
#    title_element.default = _('Untitled')
#
#    key_supported_options = {'': 'C'}
#    key_validation_pattern = r'(?i)^[A-G](#|b)?\s?(major|minor|ionian|aeolian|mixolydian|dorian|phrygian|lydian|locrian|m|maj|min|ion|aeo|mix|dor|phr|lyd|loc)'
#    key_element = AbcStructureElement('K:', _('Key'), supported_values=key_supported_options, validation_pattern=key_validation_pattern)
#    key_element.mandatory = True
#
#    meter_options = ['C', 'C|', '4/4', '3/4', '2/4', '2/2', '6/8', '9/8', '12/8', '5/8']
#
#    elements = [
#        # identification
#        index_element,
#        title_element,
#        AbcTextElement('C:', _('Composer'), multiline=True),
#        AbcTextElement('O:', _('Origin'), multiline=True),
#        AbcTextElement('R:', _('Rhythm')),
#        # background
#        AbcTextElement('B:', _('Book')),
#        AbcTextElement('D:', _('Discography'), multiline=True),
#        AbcTextElement('F:', _('File URL')),
#        AbcTextElement('G:', _('Group')),
#        AbcTextElement('H:', _('History'), multiline=True, use_line_continuation=True),
#        AbcTextElement('N:', _('Notes')),
#        AbcTextElement('S:', _('Source')),
#        AbcTextElement('Z:', _('Transcription'), multiline=True),
#        AbcTextElement('+:', _('Field continuation')),
#        AbcTextElement('s:', _('Symbol line')),
#        # structure
#        AbcStructureElement('P:', _('Parts'), description=_('How parts are repeated')),
#        AbcStructureElement('V:', _('Voices'), description=_('Which voices are present')),
#        AbcStructureElement('M:', _('Meter'), supported_values=meter_options),
#        AbcStructureElement('L:', _('Unit note length'), description=_('How long one unit is')),
#        AbcStructureElement('Q:', _('Tempo')),
#        key_element
#    ]
#    return elements


# def create_abcm2ps_elements():
#     measure_number_options = {'None': None, 'Start of every line': 0, 'Every measure': 1, 'Every 2 measures': 2, 'Every 3 measures': 3, 'Every 4 measures': 4, 'Every 5 measures': 5, 'Every 8 measures': 8, 'Every 10 measures': 10}
#     elements = [
#         Abcm2psElement('pagewidth', _('Page width'), 'unit'),
#         Abcm2psElement('pageheight', _('Page height'), 'unit'),
#         Abcm2psElement('topmargin', _('Top margin'), 'unit'),
#         Abcm2psElement('botmargin', _('Bottom margin'), 'unit'),
#         Abcm2psElement('leftmargin', _('Left margin'), 'unit'),
#         Abcm2psElement('rightmargin', _('Right margin'), 'unit'),
#         Abcm2psElement('staffwidth', _('Staff width'), 'unit'),
#         Abcm2psElement('landscape', _('Landscape'), 'bool'),
#         Abcm2psElement('scale', _('Page scale factor'), 'float'),
#         Abcm2psElement('staffscale', _('Staff scale factor'), 'float'),
#         Abcm2psElement('setbarnb', _('First measure number'), 'int'),
#         Abcm2psElement('measurenb', _('Measure numbers'), 'int', measure_number_options),
#         Abcm2psElement('measurebox', _('Box around measure number'), 'bool')
#     ]
#     return elements