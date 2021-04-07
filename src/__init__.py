import Plugins.Plugin
from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Components.config import config, ConfigSubsection, ConfigYesNo
import os, gettext
__version__ = '1.4'
PluginLangDomain = 'xModem'
PluginLangPath = 'Extensions/xModem/locale'

def localeInit():
    lang = language.getLanguage()[:2]
    os.environ['LANGUAGE'] = lang
    gettext.bindtextdomain(PluginLangDomain, resolveFilename(SCOPE_PLUGINS, PluginLangPath))


def _(txt):
    if config.plugins.xModem.nolocale.value:
        return txt
    t = gettext.dgettext(PluginLangDomain, txt)
    if t == txt:
        t = gettext.gettext(txt)
    return t


config.plugins.xModem = ConfigSubsection()
config.plugins.xModem.nolocale = ConfigYesNo(default=False)
if not config.plugins.xModem.nolocale.value:
    localeInit()
    language.addCallback(localeInit)
