from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

""" Alarm Factory: Alarm XML SAX Parser Classes """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2019-2021, European Spallation Source, Lund"
__license__    = "GPLv3"


from xml.sax.handler import ContentHandler
from xml.sax import parse as saxparser



class AlarmSaxException(Exception):
    def __init__(self, *args, **keyword_params):
        super(AlarmSaxException, self).__init__(*args)
        self.keyword_params = keyword_params



class ALARM_SAX_HANDLER(ContentHandler):
#    def __init__(self, beast_def):
#        super(ALARM_SAX_HANDLER, self).__init__()
#        self._beast_def = beast_def


    def setDef(self, beast_def):
        self._beast_def = beast_def


    def _tobool(self, text):
        return True if text == 'true' else False


    def startDocument(self):
        self._beast_def._alarm_tree = True


    def endDocument(self):
        self._beast_def._alarm_tree = False


    def startElement(self, name, attrs):
        self._beast_def._line = ("<{}>".format(name), self._locator.getLineNumber())

        if name == 'config':
            self._beast_def.config(attrs['name'])
        elif name == 'component':
            self._beast_def.xml_component(attrs['name'])
        elif name == 'pv':
            self._beast_def.pv(attrs['name'])
        elif name == 'description' or name == 'enabled' or name == 'latching' or name == 'annunciating':
            pass
        elif name == 'guidance' or name == 'display' or name == 'command' or name == 'automated_action':
            self._title = None
            self._details = None
            self._delay = None
        elif name == 'title' or name == 'details' or name == 'delay':
            pass
        else:
            raise AlarmSaxException("Unhandled opening of xml tag: {}".format(name), linenum = self._locator.getLineNumber())

        self._text = ""


    def characters(self, text):
        self._text += text


    def endElement(self, name):
        self._beast_def._line = ("</{}>".format(name), self._locator.getLineNumber())

        if name == 'component':
            self._beast_def.end_component()
        elif name == 'description':
            self._beast_def.description(self._text)
        elif name == 'enabled':
            self._beast_def.disable(not self._tobool(self._text))
        elif name == 'latching':
            self._beast_def.latching(self._tobool(self._text))
        elif name == 'annunciating':
            self._beast_def.annunciating(self._tobool(self._text))
        elif name == 'title':
            self._title = self._text
            self._beast_def.define_title(self._title, self._title)
        elif name == 'details':
            self._details = self._text
        elif name == 'delay':
            try:
                # BEAST_DEF expects a number not a string
                self._delay = int(self._text)
            except:
                # Okay, not a number. Let BEAST_DEF handle it
                self._delay = self._text
        elif name == 'guidance':
            self._beast_def.guidance(self._title, self._details)
        elif name == 'display':
            self._beast_def.display(self._title, self._details)
        elif name == 'automated_action':
            self._beast_def.automated_action(self._title, self._details, self._delay)
        elif name == 'pv':
            pass
        elif name == 'config':
            pass
        else:
            raise RuntimeError("Unhandled closing of xml tag: {}".format(name), linenum = self._locator.getLineNumber())


class ALARM_SAX_PARSER(object):
    @staticmethod
    def parse(beast_def, xml_file):
        saxhandler = ALARM_SAX_HANDLER()
        saxhandler.setDef(beast_def)

        saxparser(xml_file, saxhandler)
