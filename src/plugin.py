
run_autostart = None
plugin_version = "1.4"

def getDefaultGateway():
    if not fileExists('/proc/net/route'): return None
    f = open('/proc/net/route', 'r')
    if f:
        for line in f.readlines():
            tokens = line.split('\t')
            if tokens[1] == '00000000':
                f.close()
                return int(tokens[2], 16)

def setOptionFile(file, txt):
    system('echo "" > %s' % file)
    system('chmod 644 %s' % file)
    if not fileExists(file):
        system('mkdir /etc/ppp')
        system('mkdir /etc/ppp/ip-up.d')
        system('mkdir /etc/ppp/ip-down.d')
        system('echo "" > %s' % file)
        system('chmod 644 %s' % file)
    f = open(file, 'r+')
    if f:
        f.write(txt)
        f.close()

def setChatFile(file, txt):
    system('echo "" > %s' % file)
    system('chmod 755 %s' % file)
    if not fileExists(file):
        system('mkdir /etc/ppp')
        system('mkdir /etc/ppp/ip-up.d')
        system('mkdir /etc/ppp/ip-down.d')
        system('echo "" > %s' % file)
        system('chmod 644 %s' % file)
    f = open(file, 'r+')
    if f:
        f.write(txt)
        f.close()

def getUptime():
    if not fileExists('/proc/uptime'): return ''
    f = open('/proc/uptime', 'r')
    if f:
        for line in f.readlines():
            tokens = line.split(' ')
            if tokens[0]:
                f.close()
                return int(float(tokens[0]))

def StartConnect(autorun = False):
    global dialstate
    global logfd
    global autorestartModem
    if logfd != -1:
        logfd.close()
        logfd = -1
    if autorun == True and config.plugins.xModem.autorun.value == False:
        return -1
    if autorun:
        print '[xModem] starting autorun pppd'
        system('echo "`date` : start execute pppd" >> /tmp/autorun.log')
    print '[xModem] start execute pppd'
    doConnect()
    dialstate = DIALING
    if config.plugins.xModem.standard.value == '3':
        ret = conn.execute('pppd', 'pppd', '-d', '-detach', 'call', config.plugins.xModem.peer.file.value)
    else:
        setOptionFile('/etc/ppp/options.xmodem', setOptions())
        setChatFile('/etc/ppp/connect.chat.xmodem', setChats(True))
        setChatFile('/etc/ppp/disconnect.chat.xmodem', setChats(False))
        ret = conn.execute('pppd', 'pppd', '-d', '-detach', 'file', '/etc/ppp/options.xmodem')
    if ret:
        print '[xModem] execute pppd failed!'
        dialstate = NONE
        if autorun:
            pppdClosed(ret)
            system('echo "`date` : pppd execute failed" >> /tmp/autorun.log')
    else:
        if config.plugins.xModem.autorun.value and config.plugins.xModem.autorestart_modem.value != "0":
            if autorestartModem is None:
                autorestartModem = autoRestartModemPoller()
                if autorestartModem:
                    autorestartModem.start()
            elif not autorun:
                autorestartModem.stop()
                autorestartModem.start()
    if autorun:
        system('echo "`date` : pppd return = %d" >> /tmp/autorun.log' % ret)
    return ret

def StopConnect(autorun = False):
    global connected
    global dialstate
    global starttime
    if connected:
        if autorun:
            print '[xModem] stopping autorun pppd'
            conn.dataAvail.append(dataAvail)
        else:
            print '[xModem] stop execute pppd'
        system('killall -INT pppd')
        cnt = 0
        while fileExists('/var/run/ppp0.pid'):
            sleep(1)
            if cnt > 10:
                break
            cnt += 1

        if logfd != -1:
            pppdClosed(-1)
    connected = False
    dialstate = NONE
    starttime = None

def isHighResolution():
    return getDesktop(0).size().width() >= 1280 and getDesktop(0).size().height() >= 720

from Screens.Screen import Screen
from __init__ import _
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from enigma import eConsoleAppContainer, eTimer, gFont, gRGB, getDesktop
from Components.Label import Label
from Components.Button import Button
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, NoSave, ConfigSelection, getConfigListEntry, ConfigNothing, ConfigInteger, ConfigYesNo, ConfigText, ConfigPassword, ConfigIP, KEY_LEFT, KEY_RIGHT, KEY_0, KEY_DELETE, KEY_BACKSPACE
from Components.ActionMap import NumberActionMap, ActionMap
from Components.Language import language
from Components.Sources.Boolean import Boolean
from Components.ScrollLabel import ScrollLabel
from Components.PluginComponent import plugins
from Tools.Directories import copyfile, fileExists, resolveFilename, SCOPE_PLUGINS
from os import system, environ as os_environ, chmod
from time import time as getTime, sleep, strftime, localtime
from re import compile as re_compile, search as re_search
from Screens.Console import Console as myConsole
import gettext

def setAltDNS():
    if not fileExists('/etc/ppp/resolv.conf.xmodem'):
        return
    system("grep -v '^nameserver' /etc/ppp/resolv.conf.xmodem >/etc/resolv.conf")
    dns1 = '.'.join([ '%d' % d for d in config.plugins.xModem.dns1.value ])
    dns2 = '.'.join([ '%d' % d for d in config.plugins.xModem.dns2.value ])
    dns = 'nameserver ' + dns1 + '\nnameserver ' + dns2 + '\n'
    f = open('/etc/resolv.conf', 'r+')
    if f:
        f.seek(0, 2)
        f.write(dns)
        f.close()

def restoreDNS():
    if fileExists('/etc/ppp/resolv.conf.xmodem'):
        system('mv /etc/ppp/resolv.conf.xmodem /etc/resolv.conf')

def setOptions():
    if config.plugins.xModem.altdns.value:
        usepeerdns = ''
    else:
        usepeerdns = 'usepeerdns\n'
    if config.plugins.xModem.standard.value == '0':
        username = config.plugins.xModem.imod.username.value
        password = config.plugins.xModem.imod.password.value
        options = config.plugins.xModem.imod.port.value + '\n'
        options += '%d\n' % config.plugins.xModem.imod.speed.value
        options += 'mtu %d\n' % config.plugins.xModem.imod.mtu.value
        options += 'mru %d\n' % config.plugins.xModem.imod.mru.value
        options += 'nocrtscts\nnocdtrcts\nlocal\nlock\ndefaultroute\nasyncmap 0\n'
        options += config.plugins.xModem.imod.pppopt.value + '\n'
        options += usepeerdns
        options += "user '" + username + "'\n"
        options += "password '" + password + "'\n"
        options += 'connect \'/etc/ppp/connect.chat.xmodem "' + config.plugins.xModem.imod.number.value + '"\'\n'
        options += 'disconnect /etc/ppp/disconnect.chat.xmodem\n'
    elif config.plugins.xModem.standard.value == '1':
        if config.plugins.xModem.gprs.numbersel.value == True:
            if config.plugins.xModem.gprs.numbers.value == '3':
                gprs_number = '#777'
            elif config.plugins.xModem.gprs.numbers.value == '2':
                gprs_number = '*99**1*1#'
            elif config.plugins.xModem.gprs.numbers.value == '1':
                gprs_number = '*99***1#'
            else:
                gprs_number = '*99#'
        else:
            gprs_number = config.plugins.xModem.gprs.number.value
        username = config.plugins.xModem.gprs.username.value
        password = config.plugins.xModem.gprs.password.value
        options = config.plugins.xModem.gprs.port.value + '\n'
        options += '%d\n' % config.plugins.xModem.gprs.speed.value
        options += 'mtu %d\n' % config.plugins.xModem.gprs.mtu.value
        options += 'mru %d\n' % config.plugins.xModem.gprs.mru.value
        options += 'debug\ncrtscts\nnoipdefault\nipcp-accept-local\nlcp-echo-interval 30\nlcp-echo-failure 5\ndefaultroute\nnoauth\n'
        adv_options = 'holdoff %d\nmaxfail %d\n' % (config.plugins.xModem.holdoff.value, config.plugins.xModem.maxfail.value)
        options += adv_options
        options += config.plugins.xModem.adv_options.value + '\n'
        options += usepeerdns
        options += "user '" + username + "'\n"
        options += "password '" + password + "'\n"
        options += 'connect \'/etc/ppp/connect.chat.xmodem "' + gprs_number + '"\'\n'
        options += 'disconnect /etc/ppp/disconnect.chat.xmodem\n'
    else:
        if config.plugins.xModem.cdma.numbersel.value == True:
            if config.plugins.xModem.cdma.numbers.value == '3':
                cdma_number = '#777'
            elif config.plugins.xModem.cdma.numbers.value == '2':
                cdma_number = '*99**1*1#'
            elif config.plugins.xModem.cdma.numbers.value == '1':
                cdma_number = '*99***1#'
            else:
                cdma_number = '*99#'
        else:
            cdma_number = config.plugins.xModem.cdma.number.value
        username = config.plugins.xModem.cdma.username.value
        password = config.plugins.xModem.cdma.password.value
        options = config.plugins.xModem.cdma.port.value + '\n'
        options += '%d\n' % config.plugins.xModem.cdma.speed.value
        options += 'mtu %d\n' % config.plugins.xModem.cdma.mtu.value
        options += 'mru %d\n' % config.plugins.xModem.cdma.mru.value
        options += 'debug\ncrtscts\nnoipdefault\nipcp-accept-local\nlcp-echo-interval 30\nlcp-echo-failure 5\ndefaultroute\nnoauth\n'
        adv_options = 'holdoff %d\nmaxfail %d\n' % (config.plugins.xModem.holdoff.value, config.plugins.xModem.maxfail.value)
        options += adv_options
        options += config.plugins.xModem.adv_options.value + '\n'
        options += usepeerdns
        options += "user '" + username + "'\n"
        options += "password '" + password + "'\n"
        options += 'connect \'/etc/ppp/connect.chat.xmodem "' + cdma_number + '"\'\n'
        options += 'disconnect /etc/ppp/disconnect.chat.xmodem\n'
    return options

def setChats(init = True):
    if init:
        chatstr = '#!/bin/sh\n\nif [ $# -lt 1 ]; then\n\techo "$0: no phone number given." >&2\n\texit -1\nfi\n\nPHONENUM=$1\n\nchat -v -e \\\n'
    else:
        chatstr = '#!/bin/sh\n\nchat "" "'
    if config.plugins.xModem.standard.value == '0':
        if init:
            chatstr += 'ABORT "N" \\\nABORT "n" \\\n'
            if config.plugins.xModem.imod.initstr.value:
                chatstr += '""\t"' + config.plugins.xModem.imod.initstr.value + '" \\\n'
            else:
                chatstr += '""\t"ATZ" \\\n'
            chatstr += '"O"\t"ATD${PHONENUM}" \\\n"c"\t\n'
        elif config.plugins.xModem.imod.deinstr.value:
            chatstr += config.plugins.xModem.imod.deinstr.value + '"\n'
        else:
            chatstr += '\\d\\d+\\p+\\p+\\c" "" "\\d\\dATH0"\n'
    elif config.plugins.xModem.standard.value == '1':
        if init:
            if config.plugins.xModem.gprs.initstr.value:
                chatstr += '""\t"' + config.plugins.xModem.gprs.initstr.value + '" \\\n'
            else:
                chatstr += '""\t"ATZ" \\\n'
            chatstr += '"OK"\t\'AT+CGDCONT=1,"IP","' + config.plugins.xModem.gprs.apn.value + '"\' \\\n'
            chatstr += '"OK"\t"ATD${PHONENUM}" \\\n"CONNECT"\t""\n'
        elif config.plugins.xModem.gprs.deinstr.value:
            chatstr += config.plugins.xModem.gprs.deinstr.value + '"\n'
        else:
            chatstr += '\\d\\d+\\p+\\p+\\c" "" "\\d\\dATH"\n'
    elif init:
        if config.plugins.xModem.cdma.initstr.value:
            chatstr += '""\t"' + config.plugins.xModem.cdma.initstr.value + '"\\\n'
        else:
            chatstr += '""\t"ATZ" \\\n'
        chatstr += '"OK"\t"ATD${PHONENUM}" \\\n"CONNECT"\t""\n'
    elif config.plugins.xModem.cdma.deinstr.value:
        chatstr += config.plugins.xModem.cdma.deinstr.value + '"\n'
    else:
        chatstr += '\\d\\d+\\p+\\p+\\c" "" "\\d\\dATH"\n'
    return chatstr

def doConnect():
    global gateway
    gateway = getDefaultGateway()
    system('route del default')
    system('modprobe ppp_async')
    vendor = ''
    product = ''
    zerocdargs = ''
    enableums = False
    if config.plugins.xModem.standard.value == '1':
        vendor = config.plugins.xModem.gprs.vendid.value
        product = config.plugins.xModem.gprs.prodid.value
        enableums = config.plugins.xModem.gprs.useums.value
        if enableums:
            zerocdargs = config.plugins.xModem.gprs.umsparam.value
    elif config.plugins.xModem.standard.value == '2':
        vendor = config.plugins.xModem.cdma.vendid.value
        product = config.plugins.xModem.cdma.prodid.value
        enableums = config.plugins.xModem.cdma.useums.value
        if enableums:
            zerocdargs = config.plugins.xModem.cdma.umsparam.value
    elif config.plugins.xModem.standard.value == '3':
        vendor = config.plugins.xModem.peer.vendid.value
        product = config.plugins.xModem.peer.prodid.value
        enableums = config.plugins.xModem.peer.useums.value
        if enableums:
            zerocdargs = config.plugins.xModem.peer.umsparam.value
    modules = ['usbserial',
     'pl2303',
     'cdc_acm',
     'ftdi_sio']
    for mod in modules:
        system('modprobe -r %s' % mod)

    system('modprobe -r usbserial')

    if enableums:
        system('usb_modeswitch %s' % zerocdargs)
    if vendor and product:
        modules[0] += ' vendor=0x%s product=0x%s' % (vendor, product)
    for mod in modules:
        system('modprobe %s' % mod)

    if config.plugins.xModem.altdns.value:
        system('rm -f /etc/ppp/resolv.conf.xmodem')
        system('cp /etc/resolv.conf /etc/ppp/resolv.conf.xmodem')

def loadModemModules():
    vendor = config.plugins.xModem.gprs.vendid.value
    product = config.plugins.xModem.gprs.prodid.value
    enableums = config.plugins.xModem.gprs.useums.value
    zerocdargs = ''
    if enableums:
        zerocdargs = config.plugins.xModem.gprs.umsparam.value
    system('modprobe ppp_async')
    modules = ['usbserial',
     'pl2303',
     'cdc_acm',
     'ftdi_sio']
    for mod in modules:
        system('modprobe -r %s' % mod)
    system('modprobe -r usbserial')
    if enableums:
        system('usb_modeswitch %s' % zerocdargs)
    if vendor and product:
        modules[0] += ' vendor=0x%s product=0x%s' % (vendor, product)
    system('modprobe %s' %  modules[0])

def pppdClosed(ret):
    global logfd
    if autorestartModem:
        autorestartModem.timer.stop()
    print '[xModem] modem disconnected', ret
    if gateway:
        system('route add default gw %d.%d.%d.%d' % (gateway & 255,
         gateway >> 8 & 255,
         gateway >> 16 & 255,
         gateway >> 24 & 255))
    if config.plugins.xModem.altdns.value:
        restoreDNS()
        system('echo "`date` : restoreDNS" >> /tmp/restore.dns.log')
    if config.plugins.xModem.autorun.value:
        system('echo -e "`date` : stop execute pppd [exit code = %d]\\n" >> /tmp/autorun.log' % ret)
    if logfd != -1:
        if ret == -1:
            logfd.write(curtime2str() + ': pppd terminated because enigma2 is stop session!\n')
        else:
            logfd.write(curtime2str() + ': pppd closed and return value - %d\n' % ret)
        logfd.write(curtime2str() + ': END PPPD CONNECTION.\n')
        logfd.flush()
        logfd.close()
        logfd = -1

def curtime2str(format = '%Y/%m/%d %H:%M:%S', msec = True):
    curtime = getTime()
    ms = ''
    if msec == True:
        ms = '.%03d' % ((curtime - int(curtime)) * 1000)
    return strftime(format, localtime(curtime)) + ms

waitCR = False

def writeLog(text):
    global waitCR
    global logfd
    present = ''
    pe = text.find('\n')
    mode = config.plugins.xModem.extlog.value
    if mode == '0':
        return
    if logfd == -1:
        #if not fileExists('/etc/ppp/xmodem-connect.log'):
        #    return
        logfd = file('/etc/ppp/xmodem-connect.log', 'wb')
        logfd.write(curtime2str() + ': START PPPD CONNECTION...\n')
        waitCR = False
    if mode == '2':
        logfd.write(text)
        logfd.flush()
    else:
        if not waitCR and text == '\n':
            return
        logstr = ''
        if not mode == '1':
            shortmode = mode == '3'
            while len(text) > 0:
                if shortmode:
                    if not text[:4] == 'sent':
                        present = text[:4] == 'rcvd'
                        pe = text.find('\n')
                        if pe == -1:
                            pe = len(text) - 1
                        waitCR = waitCR and (present or False)
                        logstr += text[:pe + 1]
                elif not present:
                    logstr += curtime2str() + ': ' + text[:pe + 1]
                text = text[pe + 1:]

            len(logstr) > 0 and logfd.write(logstr)
            logfd.flush()
            waitCR = logstr[len(logstr) - 1] != '\n'

def dataAvail(text):
    global dialstate
    global starttime
    global connected
    global conn
    tmp = text
    writeLog(tmp)
    if text.find('Serial connection established') != -1:
        dialstate = LOGGING
    if text.find('AP authentication succeeded') != -1 or text.find('No auth is possible') != -1:
        dialstate = CONNECTING
    if text.find('ip-up finished') != -1:
        starttime = getUptime()
        dialstate = CONNECTED
        connected = True
        system('echo "`date` : pppd: ip-up finished" >> /tmp/autorun.log')
        if config.plugins.xModem.altdns.value:
            setAltDNS()
    if text.find('Connect script failed') != -1:
        dialstate = NONE
        system('echo "`date` : pppd: connect script failed" >> /tmp/autorun.log')
        conn.sendCtrlC()
    if text.find('ip-down finished') != -1:
        dialstate = NONE
        conn.sendCtrlC()
        connected = False
        starttime = None
        system('echo "`date` : pppd: ip-down finished" >> /tmp/autorun.log')


NONE = 0
CONNECT = 1
ABORT = 2
DISCONNECT = 3
DIALING = 1
LOGGING = 2
CONNECTING = 3
CONNECTED = 4
gateway = None
logfd = -1
connected = False
dialstate = NONE
starttime = None
autorestartModem = None
conn = eConsoleAppContainer()
conn.appClosed.append(pppdClosed)
conn.dataAvail.append(dataAvail)

config.plugins.xModem.iptables = ConfigYesNo(default=False)
config.plugins.xModem.restart_softcam = ConfigYesNo(default=False)
config.plugins.xModem.show_message = ConfigYesNo(default=False)
config.plugins.xModem.restart_softcam_preview = ConfigNothing()

config.plugins.xModem.autorestart_modem = ConfigSelection(default = "0", choices = [("0", _("disabled")) , ("15", _("15 min")), ("30", _("30 min")), ("60", _("1 hour")), ("120", _("2 hours")),("240", _("4 hours")), ("720", _("12 hours")), ("1440", _("24 hours")), ("2880", _("48 hours"))])
choices_list =[]
huawei_list = [("AT^U2DIAG=0", _("Huawei AT^U2DIAG=0 (only modem mode)")),("AT^U2DIAG=1", _("Huawei AT^U2DIAG=1 (modem and CD-Rom mode)")),("AT^U2DIAG=255", _("Huawei AT^U2DIAG=255 (Modem+CD-Rom+Card-Reader Modem+ Factory Defaults)")), ("AT^U2DIAG=256", _("Huawei AT^U2DIAG=256 (Modem+Card-Reader Mode)")), ("AT^U2DIAG=257", _("Huawei AT^U2DIAG=257 (Disable Application Port)")), ("AT^U2DIAG=276", _("Huawei AT^U2DIAG=276 (Reset to factory Defaults)")), ("AT^U2DIAG=119", _("Huawei AT^U2DIAG=119 (return to HiLink mode)")), ("AT^SYSCFG=13,1,3fffffff,0,0", _("Huawei AT^SYSCFG=13,1,3fffffff,0,0 (only 2G mode)")), ("AT^SYSCFG=2,1,3fffffff,0,0", _("Huawei AT^SYSCFG=2,1,3fffffff,0,0 (preference 2G mode)")), ("AT^SYSCFG=14,2,3fffffff,0,1 ", _("Huawei  AT^SYSCFG=14,2,3fffffff,0,1 (only 3G mode)")),("AT^SYSCFG=2,2,3fffffff,0,1", _("Huawei AT^SYSCFG=2,2,3fffffff,0,1 (preference 3G mode)")), ("AT^SYSCFG=2,2,3fffff ff,0,2", _("Huawei AT^SYSCFG=2,2,3fffff ff,0,2 (enable mode 2G and 3G)")), ("AT^SYSCFG=13,1,3FFFFFFF,2,4", _("Huawei AT^SYSCFG=13,1,3FFFFFFF,2,4 (only mode GPRS/EDGE)")), ("AT^SYSCFG=14,2,3FFFFFFF,2,4", _("Huawei AT^SYSCFG=14,2,3FFFFFFF,2,4 (only mode 3G/WCDMA)")), ("AT^SYSCFG=2,1,3FFFFFFF,2,4", _("Huawei AT^SYSCFG=2,1,3FFFFFFF,2,4 (preference mode GPRS/EDGE)")), ("AT^SYSCFG=2,2,3FFFFFFF,2,4", _("Huawei AT^SYSCFG=2,2,3FFFFFFF,2,4 (preference mode 3G/WCDMA)"))]
choices_list += huawei_list
zte_list = [("AT%USBMODEM=0", _("ZTE AT%USBMODEM=0 (only modem mode)")),("AT%USBMODEM=1", _("ZTE AT%USBMODEM=1 (modem and CD-Rom mode)")),("AT+ZSNT=0,0,0", _("ZTE AT+ZSNT=0,0,0 (Network/auto mode)")), ("AT+ZSNT=0,0,1", _("ZTE AT+ZSNT=0,0,1 (auto GSM+WCDMA/preference GSM)")), ("AT+ZSNT=0,0,2", _("ZTE AT+ZSNT=0,0,2 (auto GSM+WCDMA/preference WCDMA)")), ("AT+ZSNT=1,0,0", _("ZTE AT+ZSNT=1,0,0 (auto/only GSM)")), ("AT+ZSNT=2,0,0", _("ZTE AT+ZSNT=2,0,0 (auto/only WCDMA)")), ("AT+ZSNT=0,1,0 ", _("ZTE AT+ZSNT=0,1,0 (manual/GSM+WCDMA)")), ("AT+ZSNT=1,1,0", _("ZTE AT+ZSNT=1,1,0 (manual/only GSM)")), ("AT+ZSNT=2,1,0", _("ZTE AT+ZSNT=2,1,0  (manual/only WCDMA)"))]
choices_list += zte_list
config.plugins.xModem.examples_commands = NoSave(ConfigSelection(choices = choices_list))
config.plugins.xModem.standard = ConfigSelection([('0', _('internal modem')),
 ('1', _('GPRS/EDGE/UMTS/HSDPA')),
 ('2', 'CDMA/EVDO'),
 ('3', _('use peers file'))], default='1')
config.plugins.xModem.extlog = ConfigSelection([('0', _('none')),
 ('1', _('short')),
 ('2', _('full')),
 ('3', _('short and timestamp')),
 ('4', _('full and timestamp'))], default='1')
config.plugins.xModem.autorun = ConfigYesNo(default=False)
config.plugins.xModem.mainmenu = ConfigYesNo(default=False)
config.plugins.xModem.extmenu = ConfigYesNo(default=False)
config.plugins.xModem.altdns = ConfigYesNo(default=False)
config.plugins.xModem.maxfail = ConfigInteger(default=2, limits=(0, 30))
config.plugins.xModem.holdoff = ConfigInteger(default=60, limits=(0, 1800))
config.plugins.xModem.adv_options = ConfigSelection([('persist', _('enabled')), ('nopersist', _('disabled'))], default='persist')

config.plugins.xModem.dns1 = ConfigIP(default=[208,
 67,
 222,
 222])
config.plugins.xModem.dns2 = ConfigIP(default=[208,
 67,
 220,
 220])
config.plugins.xModem.showhints = ConfigYesNo(default=False)
config.plugins.xModem.imod = ConfigSubsection()
config.plugins.xModem.imod.username = ConfigText('arcor', fixed_size=False)
config.plugins.xModem.imod.password = ConfigPassword('internet', fixed_size=False)
config.plugins.xModem.imod.number = ConfigText('01920793', fixed_size=False)
config.plugins.xModem.imod.number.setUseableChars(u'0123456789PTW,@')
config.plugins.xModem.imod.port = ConfigText('/dev/tts/2', fixed_size=False)
config.plugins.xModem.imod.port.setUseableChars(u'0123456789abcdemstuvyABCMSTU/')
config.plugins.xModem.imod.speed = ConfigInteger(default=2400, limits=(1, 115200))
config.plugins.xModem.imod.extopt = ConfigYesNo(default=False)
config.plugins.xModem.imod.mtu = ConfigInteger(default=552, limits=(1, 65535))
config.plugins.xModem.imod.mru = ConfigInteger(default=552, limits=(1, 65535))
config.plugins.xModem.imod.initstr = ConfigText('', fixed_size=False)
config.plugins.xModem.imod.deinstr = ConfigText('', fixed_size=False)
config.plugins.xModem.imod.pppopt = ConfigText('', fixed_size=False)
config.plugins.xModem.gprs = ConfigSubsection()
config.plugins.xModem.gprs.username = ConfigText('mts', fixed_size=False)
config.plugins.xModem.gprs.password = ConfigPassword('mts', fixed_size=False)
config.plugins.xModem.gprs.number = ConfigText('*99***1#', fixed_size=False)
config.plugins.xModem.gprs.numbers = ConfigSelection([('0', '*99#'),
 ('1', '*99***1#'),
 ('2', '*99**1*1#'),
 ('3', '#777')], default='0')
config.plugins.xModem.gprs.numbersel = ConfigYesNo(default=True)
config.plugins.xModem.gprs.apn = ConfigText('internet.mts.ru', fixed_size=False)
config.plugins.xModem.gprs.port = ConfigText('/dev/ttyUSB0', fixed_size=False)
config.plugins.xModem.gprs.port.setUseableChars(u'0123456789abcdemstuvyABCMSTU/')
config.plugins.xModem.gprs.speed = ConfigInteger(default=115200, limits=(1, 921600))
config.plugins.xModem.gprs.extopt = ConfigYesNo(default=False)
config.plugins.xModem.gprs.mtu = ConfigInteger(default=1492, limits=(1, 65535))
config.plugins.xModem.gprs.mru = ConfigInteger(default=1492, limits=(1, 65535))
config.plugins.xModem.gprs.initstr = ConfigText('', fixed_size=False)
config.plugins.xModem.gprs.deinstr = ConfigText('', fixed_size=False)
config.plugins.xModem.gprs.pppopt = ConfigText('persist', fixed_size=False)
config.plugins.xModem.gprs.vendid = ConfigText('', fixed_size=False)
config.plugins.xModem.gprs.vendid.setUseableChars(u'0123456789abcdef')
config.plugins.xModem.gprs.prodid = ConfigText('', fixed_size=False)
config.plugins.xModem.gprs.prodid.setUseableChars(u'0123456789abcdef')
config.plugins.xModem.gprs.useums = ConfigYesNo(default=False)
config.plugins.xModem.gprs.umsparam = ConfigText('', fixed_size=False)
config.plugins.xModem.cdma = ConfigSubsection()
config.plugins.xModem.cdma.username = ConfigText('01920793@free', fixed_size=False)
config.plugins.xModem.cdma.password = ConfigPassword('000000', fixed_size=False)
config.plugins.xModem.cdma.number = ConfigText('#777', fixed_size=False)
config.plugins.xModem.cdma.numbers = ConfigSelection([('0', '*99#'),
 ('1', '*99***1#'),
 ('2', '*99**1*1#'),
 ('3', '#777')], default='3')
config.plugins.xModem.cdma.numbersel = ConfigYesNo(default=True)
config.plugins.xModem.cdma.port = ConfigText('/dev/ttyUSB0', fixed_size=False)
config.plugins.xModem.cdma.port.setUseableChars(u'0123456789abcdemstuvyABCMSTU/')
config.plugins.xModem.cdma.speed = ConfigInteger(default=460800, limits=(1, 921600))
config.plugins.xModem.cdma.mtu = ConfigInteger(default=1492, limits=(1, 65535))
config.plugins.xModem.cdma.mru = ConfigInteger(default=1492, limits=(1, 65535))
config.plugins.xModem.cdma.initstr = ConfigText('', fixed_size=False)
config.plugins.xModem.cdma.deinstr = ConfigText('', fixed_size=False)
config.plugins.xModem.cdma.pppopt = ConfigText('persist', fixed_size=False)
config.plugins.xModem.cdma.vendid = ConfigText('', fixed_size=False)
config.plugins.xModem.cdma.vendid.setUseableChars(u'0123456789abcdef')
config.plugins.xModem.cdma.prodid = ConfigText('', fixed_size=False)
config.plugins.xModem.cdma.prodid.setUseableChars(u'0123456789abcdef')
config.plugins.xModem.cdma.useums = ConfigYesNo(default=False)
config.plugins.xModem.cdma.umsparam = ConfigText('', fixed_size=False)
config.plugins.xModem.peer = ConfigSubsection()
config.plugins.xModem.peer.file = ConfigText('gprs-siem', fixed_size=False)
config.plugins.xModem.peer.vendid = ConfigText('', fixed_size=False)
config.plugins.xModem.peer.vendid.setUseableChars(u'0123456789abcdef')
config.plugins.xModem.peer.prodid = ConfigText('', fixed_size=False)
config.plugins.xModem.peer.prodid.setUseableChars(u'0123456789abcdef')
config.plugins.xModem.peer.useums = ConfigYesNo(default=False)
config.plugins.xModem.peer.umsparam = ConfigText('', fixed_size=False)

plugin_version = '1.3'
from autoRestartModemPoller import autoRestartModemPoller

class ConnectInfo(Screen):
    skin = """
        <screen position="center,center" size="440,310" title="Connect statistics" >
        <ePixmap pixmap="skin_default/buttons/red.png" position="10,10" size="140,40" alphatest="on" />
        <widget name="key_red" position="10,10" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
        <widget name="contimetxt" position="10,60" size="180,18" font="Regular;16" transparent="1" />
        <widget name="contimeval" position="200,60" size="235,18" font="Regular;16" />
        <widget name="ifacetxt" position="10,80" size="180,18" font="Regular;16" transparent="1" />
        <widget name="ifaceval" position="200,80" size="235,18" font="Regular;16" />
        <widget name="localIPtxt" position="10,100" size="180,18" font="Regular;16" transparent="1" />
        <widget name="localIPval" position="200,100" size="235,18" font="Regular;16" transparent="1" />
        <widget name="remoteIPtxt" position="10,120" size="180,18" font="Regular;16" transparent="1" />
        <widget name="remoteIPval" position="200,120" size="235,18" font="Regular;16" transparent="1" />
        <widget name="gatewaytxt" position="10,140" size="180,18" font="Regular;16" transparent="1" />
        <widget name="gatewayval" position="200,140" size="235,18" font="Regular;16" transparent="1" />
        <widget name="dnstxt" position="10,160" size="180,18" font="Regular;16" transparent="1" />
        <widget name="dnsval" position="200,160" size="235,18" font="Regular;15" transparent="1" />
        <ePixmap pixmap="skin_default/div-v.png" position="98,205" size="2,90" zPosition="1" />
        <ePixmap pixmap="skin_default/div-v.png" position="268,205" size="2,90" zPosition="1" />
        <widget name="receivetxt" position="100,205" size="165,18" font="Regular;16" halign="center" transparent="1" />
        <widget name="transmittxt" position="270,205" size="165,18" font="Regular;16" halign="center" transparent="1" />
        <ePixmap pixmap="skin_default/div-h.png" position="10,230" size="420,2" zPosition="1" />
        <widget name="bytestxt" position="10,240" size="85,18" font="Regular;16" transparent="1" />
        <widget name="bytesRXval" position="100,240" size="165,18" font="Regular;16" halign="center" transparent="1" />
        <widget name="bytesTXval" position="270,240" size="165,18" font="Regular;16" halign="center" transparent="1" />
        <widget name="packettxt" position="10,260" size="85,18" font="Regular;16" transparent="1" />
        <widget name="packetRXval" position="100,260" size="165,18" font="Regular;16" halign="center" transparent="1" />
        <widget name="packetTXval" position="270,260" size="165,18" font="Regular;16" halign="center" transparent="1" />
        <widget name="errortxt" position="10,280" size="85,18" font="Regular;16" transparent="1" />
        <widget name="errorRXval" position="100,280" size="165,18" font="Regular;16" halign="center" transparent="1" />
        <widget name="errorTXval" position="270,280" size="165,18" font="Regular;16" halign="center" transparent="1" />
        </screen>"""

    def __init__(self, session, constarttime = None, iface = 'ppp0'):
        Screen.__init__(self, session)
        self.starttime = constarttime
        if self.starttime is None:
            self.starttime = getUptime()
        self.iface = iface
        if self.iface is None:
            self.iface = 'ppp0'
        self.Console = None
        self.getInterface(self.iface)
        self['Title'].text = _('Connect statistics')
        self['key_red'] = Button(_('Close'))
        self['ifacetxt'] = Label(_('Interface:'))
        self['ifaceval'] = Label(self.iface)
        self['curtimetxt'] = Label(_('Current Time:'))
        self['contimetxt'] = Label(_('Connection Time:'))
        self['contimeval'] = Label(self.getConnectTime())
        self['localIPtxt'] = Label(_('Local IP:'))
        self['localIPval'] = Label('-.-.-.-')
        self['remoteIPtxt'] = Label(_('Remote IP:'))
        self['remoteIPval'] = Label('-.-.-.-')
        self['gatewaytxt'] = Label(_('Gateway:'))
        self['gatewayval'] = Label(self.getGateway())
        self['dnstxt'] = Label(_('Nameservers:'))
        self['dnsval'] = Label(self.getNameservers())
        self['receivetxt'] = Label(_('Received'))
        self['transmittxt'] = Label(_('Transmited'))
        self['bytestxt'] = Label(_('Bytes:'))
        self['bytesRXval'] = Label('0')
        self['bytesTXval'] = Label('0')
        self['packettxt'] = Label(_('Packets:'))
        self['packetRXval'] = Label('0')
        self['packetTXval'] = Label('0')
        self['errortxt'] = Label(_('Errors:'))
        self['errorRXval'] = Label('0')
        self['errorTXval'] = Label('0')
        self.getStatistics(self.iface)
        self['actions'] = ActionMap(['ConnectInfoActions'], {'cancel': self.close,
         'ok': self.close})
        self.clock_timer = eTimer()
        self.clock_timer.callback.append(self.clockLoop)
        self.onClose.append(self.__closed)
        self.onLayoutFinish.append(self.__layoutFinished)

    def __layoutFinished(self):
        self.clock_timer.start(1000, False)

    def __closed(self):
        self.clock_timer.stop()
        self.clock_timer.callback.remove(self.clockLoop)

    def clockLoop(self):
        self['contimeval'].setText(self.getConnectTime())
        self.getStatistics(self.iface)

    def getConnectTime(self):
        uptime = getUptime()
        if uptime and self.starttime:
            time = int(uptime - self.starttime)
        else:
            time = 0
        s = time % 60
        m = time / 60 % 60
        h = time / 3600 % 24
        d = time / 86400
        text = '%02d:%02d:%02d' % (h, m, s)
        if d > 0:
            text = '%dd %s' % (d, text)
        return text

    def getGateway(self):
        gw = getDefaultGateway()
        if gw:
            return '%d.%d.%d.%d' % (gw & 255,
             gw >> 8 & 255,
             gw >> 16 & 255,
             gw >> 24 & 255)
        return '0.0.0.0'

    def regExpMatch(self, pattern, string):
        if string is None:
            return
        try:
            return pattern.search(string).group()
        except AttributeError:
            None

    def getNameservers(self):
        ipRegexp = '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}'
        nameserverPattern = re_compile('^nameserver +' + ipRegexp)
        ipPattern = re_compile(ipRegexp)
        resolv = []
        try:
            fp = file('/etc/resolv.conf', 'r')
            resolv = fp.readlines()
            fp.close()
        except:
            print '[xModem] resolv.conf - opening failed'

        servers = ''
        for line in resolv:
            if self.regExpMatch(nameserverPattern, line) is not None:
                ip = self.regExpMatch(ipPattern, line)
                if ip is not None:
                    if servers:
                        servers += '; ' + ip
                    else:
                        servers = ip

        return servers

    def getStatistics(self, iface = 'ppp0'):
        digitalPattern = re_compile('[0-9]+')
        proclines = []
        try:
            fp = file('/proc/net/dev', 'r')
            proclines = fp.readlines()
            fp.close()
        except:
            print '[xModem] /proc/net/dev - opening failed'

        for line in proclines:
            if line.find(iface) != -1:
                tokens = digitalPattern.findall(line[7:])
                if len(tokens) > 10:
                    self['bytesRXval'].setText(self.strToSize(tokens[0]))
                    self['packetRXval'].setText(tokens[1])
                    self['errorRXval'].setText(tokens[2])
                    self['bytesTXval'].setText(self.strToSize(tokens[8]))
                    self['packetTXval'].setText(tokens[9])
                    self['errorTXval'].setText(tokens[10])
                break

    def strToSize(self, strval = '0'):
        ext = ['KB',
         'KB',
         'MB',
         'GB',
         'TB']
        X = int(strval)
        D = 0
        M = X
        i = 0
        while X > 1023:
            D = X / 1024
            M = X % 1024
            X = D
            i += 1
            if i > 3:
                break

        return '%lu,%.3lu %s' % (D, M * 1000 / 1024, ext[i])

    def getInterface(self, iface):
        from Components.Console import Console
        if not self.Console:
            self.Console = Console()
        cmd = 'ip -o addr'
        self.Console.ePopen(cmd, self.IPaddrFinished, iface)

    def IPaddrFinished(self, result, retval, extra_args):
        iface = extra_args
        globalIPpattern = re_compile('scope global')
        ipRegexp = '[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}'
        ipLinePattern = re_compile('inet ' + ipRegexp)
        peerLinePattern = re_compile('peer ' + ipRegexp + '/')
        ipPattern = re_compile(ipRegexp)
        for line in result.splitlines():
            split = line.strip().split(' ', 2)
            if split[1] == iface:
                if re_search(globalIPpattern, split[2]):
                    ip = self.regExpMatch(ipPattern, self.regExpMatch(ipLinePattern, split[2]))
                    peer = self.regExpMatch(ipPattern, self.regExpMatch(peerLinePattern, split[2]))
                    if ip is not None:
                        self['localIPval'].setText(ip)
                    if peer is not None:
                        self['remoteIPval'].setText(peer)


class LogConsole(Screen):
    if not isHighResolution():
        skin = """
            <screen position="center,center" size="600,400" title="Log..." >
            <widget name="text" position="0,0" size="600,400" font="Console;14" />
            </screen>"""
    else:
        skin = """
            <screen position="center,center" size="1080,520" title="Log..." >
            <widget name="text" position="0,0" size="1080,520" font="Console;16" />
            </screen>"""

    def __init__(self, session, title = 'Log...', logfile = '', lines = 333, scroll = False):
        self.skin = LogConsole.skin
        Screen.__init__(self, session)
        self['text'] = ScrollLabel('')
        self['actions'] = ActionMap(['LogConsoleActions'], {'ok': self.cancel,
         'back': self.cancel,
         'text': self.cancel,
         'up': self['text'].pageUp,
         'down': self['text'].pageDown,
         'moveTop': self.moveTop,
         'moveEnd': self['text'].lastPage}, -1)
        self.title = title
        self.cmd = 'tail -n %d -f %s' % (lines, logfile)
        self.scroll = scroll
        self.title = _('Log...')
        self.onShown.append(self.updateTitle)
        self.container = eConsoleAppContainer()
        self.container.appClosed.append(self.runFinished)
        self.container.dataAvail.append(self.dataAvail)
        self.onLayoutFinish.append(self.startRun)

    def updateTitle(self):
        self.setTitle(self.title)

    def startRun(self):
        if self.container.execute(self.cmd):
            self.runFinished(-1)

    def runFinished(self, retval):
        if retval:
            self['text'].setText('Log execute failed!')
        if self.scroll:
            self['text'].lastPage()

    def cancel(self):
        self.container.sendCtrlC()
        self.close()
        self.container.appClosed.remove(self.runFinished)
        self.container.dataAvail.remove(self.dataAvail)

    def moveTop(self):
        i = self['text'].pages
        while i > 1:
            self['text'].pageUp()
            i -= 1
            self['text'].updateScrollbar()

    def dataAvail(self, txt):
        self['text'].appendText(txt)
        if self.scroll:
            self['text'].lastPage()

class dataConsole(myConsole):
    def __init__(self, session, title = "execute...", cmdlist = None, finishedCallback = None, closeOnSuccess = False):
		myConsole.__init__(self, session, title, cmdlist, finishedCallback, closeOnSuccess)
		self.skinName = "Console"
		self["BackupActions"] = ActionMap(["InfobarMenuActions"], 
		{
			"mainMenu": self.stopRun,
		}, -2)
		self.stop_run = False
		self.title = _('execute...')

    def cancel(self):
		if not self.stop_run:
			self.container.sendCtrlC()
		self.close()
		self.container.appClosed.remove(self.runFinished)
		self.container.dataAvail.remove(self.dataAvail)
 
    def stopRun(self):
		if not self.stop_run:
			self.container.sendCtrlC()
			self.stop_run = True

class ModemSetup(ConfigListScreen, Screen):
    if not isHighResolution():
        skin = """
            <screen position="center,center" size="560,400" title="xModem" >
            <ePixmap position="0,0"   zPosition="2" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
            <ePixmap position="140,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
            <ePixmap position="280,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" /> 
            <ePixmap position="420,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" /> 
            <widget name="key_red" position="0,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;18" transparent="1" shadowColor="background" shadowOffset="-2,-2" /> 
            <widget name="key_green" position="140,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;18" transparent="1" shadowColor="background" shadowOffset="-2,-2" /> 
            <widget name="key_yellow" position="280,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;18" transparent="1" shadowColor="background" shadowOffset="-2,-2" />
            <widget name="key_blue" position="420,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;18" transparent="1" shadowColor="background" shadowOffset="-2,-2" />
            <widget name="config" position="25,60" size="520,226" scrollbarMode="showOnDemand" />
            <ePixmap pixmap="skin_default/div-h.png" position="35,293" size="455,2" zPosition="1" />
            <ePixmap pixmap="skin_default/div-v.png" position="35,295" size="2,102" zPosition="1" />
            <ePixmap pixmap="skin_default/div-v.png" position="488,295" size="2,102" zPosition="1" />
            <widget name="status" position="37,300" size="455,100" font="Regular;16" foregroundColor="#abcdef" />
            <ePixmap pixmap="skin_default/div-h.png" position="35,398" size="455,2" zPosition="1" />
            <widget source="TvIcon" render="Pixmap" pixmap="%s" position="0,295" zPosition="10" size="35,25" transparent="1" alphatest="on" >
                <convert type="ConditionalShowHide" />
            </widget>
            <widget source="InfoIcon" render="Pixmap" pixmap="%s" position="510,295" zPosition="10" size="35,25" transparent="1" alphatest="on" >
                <convert type="ConditionalShowHide" />
            </widget>
            <widget source="TextIcon" render="Pixmap" pixmap="%s" position="510,345" zPosition="10" size="35,25" transparent="1" alphatest="on" >
                <convert type="ConditionalShowHide" />
            </widget>
            <ePixmap pixmap="%s" position="510,370" zPosition="10" size="35,25" transparent="1" alphatest="on" />
            <ePixmap pixmap="%s" position="0,370" zPosition="10" size="35,25" transparent="1" alphatest="on" />
            </screen>""" % (resolveFilename(SCOPE_PLUGINS, 'Extensions/xModem/images/key_tv.png'), resolveFilename(SCOPE_PLUGINS, 'Extensions/xModem/images/key_info.png'), resolveFilename(SCOPE_PLUGINS, 'Extensions/xModem/images/key_text.png'), resolveFilename(SCOPE_PLUGINS, 'Extensions/xModem/images/key_help.png'), resolveFilename(SCOPE_PLUGINS, 'Extensions/xModem/images/key_menu.png'))
    else:
        skin = """
            <screen position="center,center" size="800,400" title="xModem" >
            <ePixmap position="0,43" zPosition="1" size="200,2" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/xModem/images/red.png" alphatest="blend" />
            <widget name="key_red" position="0,10" zPosition="2" size="200,30" font="Regular; 21" halign="center" valign="center" backgroundColor="background" foregroundColor="white" transparent="1" />
            <ePixmap position="200,43" zPosition="1" size="200,2" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/xModem/images/green.png" alphatest="blend" />
            <widget name="key_green" position="200,10" zPosition="2" size="200,30" font="Regular; 21" halign="center" valign="center" backgroundColor="background" foregroundColor="white" transparent="1" />
            <ePixmap position="400,43" zPosition="1" size="200,2" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/xModem/images/yellow.png" alphatest="blend" />
            <widget name="key_yellow" position="400,10" zPosition="2" size="200,30" font="Regular; 21" halign="center" valign="center" backgroundColor="background" foregroundColor="white" transparent="1" />
            <ePixmap position="600,43" zPosition="1" size="200,2" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/xModem/images/blue.png" alphatest="blend" />
            <widget name="key_blue" position="600,0" zPosition="2" size="200,42" font="Regular; 19" halign="center" valign="center" backgroundColor="background" foregroundColor="white" transparent="1" />
            <widget name="config" position="50,60" size="700,226" scrollbarMode="showOnDemand" />
            <ePixmap pixmap="skin_default/div-h.png" position="50,293" size="655,2" zPosition="1" />
            <ePixmap pixmap="skin_default/div-v.png" position="50,295" size="2,95" zPosition="1" />
            <ePixmap pixmap="skin_default/div-v.png" position="703,295" size="2,95" zPosition="1" />
            <widget name="status" position="53,300" size="650,97" font="Regular;17" foregroundColor="#abcdef" />
            <ePixmap pixmap="skin_default/div-h.png" position="50,390" size="655,2" zPosition="1" />
            <widget source="TvIcon" render="Pixmap" pixmap="%s" position="0,295" zPosition="10" size="35,25" transparent="1" alphatest="on" >
                <convert type="ConditionalShowHide" />
            </widget>
            <widget source="InfoIcon" render="Pixmap" pixmap="%s" position="725,295" zPosition="10" size="35,25" transparent="1" alphatest="on" >
                <convert type="ConditionalShowHide" />
            </widget>
            <widget source="TextIcon" render="Pixmap" pixmap="%s" position="725,345" zPosition="10" size="35,25" transparent="1" alphatest="on" >
                <convert type="ConditionalShowHide" />
            </widget>
            <ePixmap pixmap="%s" position="725,370" zPosition="10" size="35,25" transparent="1" alphatest="on" />
            <ePixmap pixmap="%s" position="0,370" zPosition="10" size="35,25" transparent="1" alphatest="on" />
            </screen>""" % (resolveFilename(SCOPE_PLUGINS, 'Extensions/xModem/images/key_tv.png'), resolveFilename(SCOPE_PLUGINS, 'Extensions/xModem/images/key_info.png'), resolveFilename(SCOPE_PLUGINS, 'Extensions/xModem/images/key_text.png'), resolveFilename(SCOPE_PLUGINS, 'Extensions/xModem/images/key_help.png'), resolveFilename(SCOPE_PLUGINS, 'Extensions/xModem/images/key_menu.png'))

    def nothing(self):
        pass

    def __init__(self, session, args = None):
        self.skin = ModemSetup.skin
        self.dot = 0
        self.dots = '........'
        self.connectiface = None
        self.green_function = NONE
        self.red_function = NONE
        self.statuscolors = [gRGB(11259375), gRGB(13421772)]
        self.hints = []
        Screen.__init__(self, session)
        ConfigListScreen.__init__(self, [])
        self.initConfig()
        self['Title'].text = _('xModem setup') + ": " + plugin_version
        self['key_green'] = Button('')
        self['key_red'] = Button('')
        self['key_yellow'] = Button('')
        self['key_blue'] = Button('')
        self['status'] = Label('')
        self['TvIcon'] = Boolean(False)
        self['InfoIcon'] = Boolean(False)
        self['TextIcon'] = Boolean(False)
        self['actions'] = NumberActionMap(['xModemActions'], {'ok': self.keyOK,
         'left': self.keyLeft,
         'right': self.keyRight,
         'cancel': self.keyExit,
         'moveUp': self.keyUp,
         'moveDown': self.keyDown,
         'connect': self.connect,
         'disconnect': self.disconnect,
         'info': self.showInfo,
         'logtext': self.showLog,
         'showHints': self.showHints,
         'openmenu': self.openMenu,
         'vk': self.openVK,
         'deleteForward': self.deleteForward,
         'deleteBackward': self.deleteBackward,
         '0': self.keyNumber,
         '1': self.keyNumber,
         '2': self.keyNumber,
         '3': self.keyNumber,
         '4': self.keyNumber,
         '5': self.keyNumber,
         '6': self.keyNumber,
         '7': self.keyNumber,
         '8': self.keyNumber,
         '9': self.keyNumber}, -1)
        self['ListActions'] = ActionMap(['ListboxDisableActions'], {'moveTop': self.nothing,
         'moveEnd': self.nothing,
         'pageUp': self.nothing,
         'pageDown': self.nothing}, -1)
        self.stateTimer = eTimer()
        self.stateTimer.callback.append(self.stateLoop)
        conn.appClosed.append(self.pppdClosed)
        conn.dataAvail.append(self.dataAvail)
        conn.dataAvail.remove(dataAvail)
        self.onClose.append(self.__closed)
        self.onLayoutFinish.append(self.__layoutFinished)
        self.prev_extmenu = config.plugins.xModem.extmenu.value
        self.autorestart_modem = config.plugins.xModem.autorestart_modem.value

    def initConfig(self):
		list = []
		self.extopt = None
		self.numbers = None
		self.useums = None
		self.autostart = None
		self.adv_options = None
		self.autorestart = None
		self.standard = getConfigListEntry(_('Standard'), config.plugins.xModem.standard)
		list.append(self.standard)
		if config.plugins.xModem.standard.value == '0':
			list.append(getConfigListEntry(_('Username'), config.plugins.xModem.imod.username))
			list.append(getConfigListEntry(_('Password'), config.plugins.xModem.imod.password))
			list.append(getConfigListEntry(_('Phone number'), config.plugins.xModem.imod.number))
			self.extopt = getConfigListEntry(_('Extended settings'), config.plugins.xModem.imod.extopt)
			list.append(self.extopt)
			if config.plugins.xModem.imod.extopt.value == True:
				sublist = [getConfigListEntry(_('Port'), config.plugins.xModem.imod.port),
				getConfigListEntry(_('Speed'), config.plugins.xModem.imod.speed),
				getConfigListEntry(_('MTU size'), config.plugins.xModem.imod.mtu),
				getConfigListEntry(_('MRU size'), config.plugins.xModem.imod.mru),
				getConfigListEntry(_('Init string'), config.plugins.xModem.imod.initstr),
				getConfigListEntry(_('Deinit string'), config.plugins.xModem.imod.deinstr),
				getConfigListEntry(_('Examples_AT-commands'), config.plugins.xModem.examples_commands),
				getConfigListEntry(_('Adv. pppd options'), config.plugins.xModem.imod.pppopt)]
				list.extend(sublist)
		elif config.plugins.xModem.standard.value == '1':
			list.append(getConfigListEntry(_('Username'), config.plugins.xModem.gprs.username))
			list.append(getConfigListEntry(_('Password'), config.plugins.xModem.gprs.password))
			if config.plugins.xModem.gprs.numbersel.value == True:
				self.numbers = getConfigListEntry(_('Phone number'), config.plugins.xModem.gprs.numbers)
				list.append(self.numbers)
			else:
				list.append(getConfigListEntry(_('Phone number'), config.plugins.xModem.gprs.number))
			list.append(getConfigListEntry(_('APN'), config.plugins.xModem.gprs.apn))
			list.append(getConfigListEntry(_('Port'), config.plugins.xModem.gprs.port))
			list.append(getConfigListEntry(_('Speed'), config.plugins.xModem.gprs.speed))
			self.extopt = getConfigListEntry(_('Extended settings'), config.plugins.xModem.gprs.extopt)
			list.append(self.extopt)
			if config.plugins.xModem.gprs.extopt.value == True:
				sublist = [getConfigListEntry(_('MTU size'), config.plugins.xModem.gprs.mtu),
				getConfigListEntry(_('MRU size'), config.plugins.xModem.gprs.mru),
				getConfigListEntry(_('Init string'), config.plugins.xModem.gprs.initstr),
				getConfigListEntry(_('Deinit string'), config.plugins.xModem.gprs.deinstr),
				getConfigListEntry(_('Examples_AT-commands'), config.plugins.xModem.examples_commands),
				#getConfigListEntry(_('Adv. pppd options'), config.plugins.xModem.gprs.pppopt),
				getConfigListEntry(_('Vendor ID'), config.plugins.xModem.gprs.vendid),
				getConfigListEntry(_('Product ID'), config.plugins.xModem.gprs.prodid)]
				self.useums = getConfigListEntry(_('Use usb_modeswitch'), config.plugins.xModem.gprs.useums)
				sublist.append(self.useums)
				if config.plugins.xModem.gprs.useums.value == True:
					sublist.extend([getConfigListEntry(_('usb_modeswitch params'), config.plugins.xModem.gprs.umsparam)])
				list.extend(sublist)
				self.adv_options = getConfigListEntry(_('Persistent dialing'), config.plugins.xModem.adv_options)
				list.append(self.adv_options)
				if config.plugins.xModem.adv_options.value == "persist":
					list.append(getConfigListEntry(_('Quantity failed attempts'), config.plugins.xModem.maxfail))
					list.append(getConfigListEntry(_('Delay between attempts (sec)'), config.plugins.xModem.holdoff))
		elif config.plugins.xModem.standard.value == '2':
			list.append(getConfigListEntry(_('Username'), config.plugins.xModem.cdma.username))
			list.append(getConfigListEntry(_('Password'), config.plugins.xModem.cdma.password))
			if config.plugins.xModem.cdma.numbersel.value == True:
				self.numbers = getConfigListEntry(_('Phone number'), config.plugins.xModem.cdma.numbers)
				list.append(self.numbers)
			else:
				list.append(getConfigListEntry(_('Phone number'), config.plugins.xModem.cdma.number))
			list.append(getConfigListEntry(_('Port'), config.plugins.xModem.cdma.port))
			list.append(getConfigListEntry(_('Speed'), config.plugins.xModem.cdma.speed))
			list.append(getConfigListEntry(_('MTU size'), config.plugins.xModem.cdma.mtu))
			list.append(getConfigListEntry(_('MRU size'), config.plugins.xModem.cdma.mru))
			list.append(getConfigListEntry(_('Init string'), config.plugins.xModem.cdma.initstr))
			list.append(getConfigListEntry(_('Deinit string'), config.plugins.xModem.cdma.deinstr))
			#list.append(getConfigListEntry(_('Adv. pppd options'), config.plugins.xModem.cdma.pppopt))
			list.append(getConfigListEntry(_('Vendor ID'), config.plugins.xModem.cdma.vendid))
			list.append(getConfigListEntry(_('Product ID'), config.plugins.xModem.cdma.prodid))
			self.useums = getConfigListEntry(_('Use usb_modeswitch'), config.plugins.xModem.cdma.useums)
			list.append(self.useums)
			if config.plugins.xModem.cdma.useums.value == True:
				list.extend([getConfigListEntry(_('usb_modeswitch params'), config.plugins.xModem.cdma.umsparam)])
			self.adv_options = getConfigListEntry(_('Persistent dialing'), config.plugins.xModem.adv_options)
			list.append(self.adv_options)
			if config.plugins.xModem.adv_options.value == "persist":
				list.append(getConfigListEntry(_('Quantity failed attempts'), config.plugins.xModem.maxfail))
				list.append(getConfigListEntry(_('Delay between attempts (sec)'), config.plugins.xModem.holdoff))
		else:
			list.append(getConfigListEntry(_('File /etc/ppp/peers/'), config.plugins.xModem.peer.file))
			list.append(getConfigListEntry(_('Vendor ID'), config.plugins.xModem.peer.vendid))
			list.append(getConfigListEntry(_('Product ID'), config.plugins.xModem.peer.prodid))
			self.useums = getConfigListEntry(_('Use usb_modeswitch'), config.plugins.xModem.peer.useums)
			list.append(self.useums)
			if config.plugins.xModem.peer.useums.value == True:
				list.extend([getConfigListEntry(_('usb_modeswitch params'), config.plugins.xModem.peer.umsparam)])
		self.altdns = getConfigListEntry(_('Alternative DNS'), config.plugins.xModem.altdns)
		list.append(self.altdns)
		if config.plugins.xModem.altdns.value == True:
			sublist2 = [getConfigListEntry(_('Primary DNS'), config.plugins.xModem.dns1), getConfigListEntry(_('Secondary DNS'), config.plugins.xModem.dns2)]
			list.extend(sublist2)
		list.append(getConfigListEntry(_('Extended log'), config.plugins.xModem.extlog))
		if fileExists('/usr/sbin/xtables-multi'):
			list.append(getConfigListEntry(_('Use firewall'), config.plugins.xModem.iptables))
		else:
			config.plugins.xModem.iptables.value = False
		if fileExists("/etc/init.d/softcam") or fileExists("/etc/init.d/cardserver") or fileExists('/usr/lib/enigma2/python/Plugins/Extensions/xModem/10user_emurestart'):
			list.append(getConfigListEntry(_('Restart softcam'), config.plugins.xModem.restart_softcam))
		else:
			list.append(getConfigListEntry(_('Restart softcam (readme)'), config.plugins.xModem.restart_softcam_preview))
		self.autostart = getConfigListEntry(_('Autostart modem'), config.plugins.xModem.autorun)
		list.append(self.autostart)
		if config.plugins.xModem.autorun.value == True:
			self.autorestart = getConfigListEntry(_('Autorestart modem'), config.plugins.xModem.autorestart_modem)
			list.append(self.autorestart)
			if config.plugins.xModem.autorestart_modem.value != "0":
				list.append(getConfigListEntry(_('Show message before restart'), config.plugins.xModem.show_message))
		list.append(getConfigListEntry(_('xModem on mainmenu'), config.plugins.xModem.mainmenu))
		list.append(getConfigListEntry(_('xModem on extensions menu'), config.plugins.xModem.extmenu))
		self['config'].list = list
		self['config'].l.setList(list)

    def initHints(self):
        self.hints = [('Standard', 'Press left/right button to change connection type.'),
         ('Username', 'Use number buttons on your remote control to change login for internet access.\nFor help contact with your mobile operator.'),
         ('Password', 'Use number buttons on your remote control to change password for internet access.\nFor help contact with your mobile operator.'),
         ('Phone number', 'Use number buttons on your remote control to change dial-up number.\nFor help contact with your mobile operator.'),
         ('Extended settings', 'Press left/right button to enable/disable extended settings.'),
         ('Port', "Use number buttons on your remote control to change modem port.\nUse 'dmesg' command to get device path your modems."),
         ('Speed', 'Use number buttons on your remote control to change speed of modem port.'),
         ('MTU size', 'Use number buttons on your remote control to change MTU size.'),
         ('MRU size', 'Use number buttons on your remote control to change MRU size.'),
         ('Init string', 'Use number buttons on your remote control to change Init string.\nAllowed only AT-commands (e.g.: ATE1D2S0=0).'),
         ('Deinit string', 'Use number buttons on your remote control to change Deinit string.\nAllowed only AT-commands (e.g.: ATH0).'),
         ('Adv. pppd options', 'Use number buttons on your remote control to change advanced pppd options.\nFor help see pppd documentation...'),
         ('Persistent dialing', 'When enabled, do not exit after a connection is terminated, instead try to reopen the connection.'),
         ('Quantity failed attempts', 'Terminate after n consecutive failed connection attempts.\nA value of 0 means no limit.'),
         ('Delay between attempts (sec)', 'Specifies how many seconds to wait before re-initiating the link after it terminates.'),
         ('Alternative DNS', 'Press left/right button to enable/disable alternative DNS.'),
         ('Primary DNS', 'Use number buttons on your remote control to change Primary DNS.'),
         ('Secondary DNS', 'Use number buttons on your remote control to change Secondary DNS.'),
         ('Restart softcam', 'Press left/right button to enable/disable restarting softcam and cardserver after connection modem.'),
         ('Restart softcam (readme)', "User script '10user_emurestart' for restarting softcam after connection modem need add to /usr/lib/enigma2/python/Plugins/Extensions/xModem/"),
         ('Autostart modem', 'Press left/right button to enable/disable autorun connection on start Enigma2.'),
         ('Autorestart modem', 'Set the time after which the modem will be forced automatically reconnected.'),
         ('xModem on mainmenu', 'Show/Hide plugin xModem on mainmenu.\nWithout restarting GUI.'),
         ('xModem on extensions menu', 'Show/Hide plugin xModem on extensions menu.\nWithout restarting GUI.'),
         ('Extended log', 'Press left/right button to disable or enable and select extended log mode.\nYou can view log on press TEXT button.'),
         ('APN', 'Use number buttons on your remote control to change Access Point Name.\nFor help contact with your mobile operator.'),
         ('Vendor ID', "Use number buttons on your remote control to change Vendor ID.\nAllowed only 4 hexdigits, without prefix '0x'.\nUse 'lsusb' command to get Vendor ID value."),
         ('Product ID', "Use number buttons on your remote control to change Product ID.\nAllowed only 4 hexdigits, without prefix '0x'.\nUse 'lsusb' command to get Product ID value."),
         ('Use usb_modeswitch', "Press left/right button to enable/disable usage 'usb_modeswitch' command."),
         ('Show message before restart', "When enabled, show display notification (timeout 15 sec.) before forced restart modem. Only use live tv."),
         ('Examples_AT-commands', "Press left/right button to change AT-commands, e.g. switch to only the modem (tools picocom) or mode 2G only (press OK)."),
         ('usb_modeswitch params', "Use number buttons on your remote control to set usb_modeswitch parameters. For help see usb_modeswitch documentation or use 'usb_modeswitch --help' command.", "Example:'-R -c /ect/usb_modeswitch.conf' or 'usb_modeswitch -v[Vendor ID] -p[Product ID] -c /usr/share/usb_modeswitch/[Vendor ID]:[Product ID]'"),
         ('Use firewall', 'Press left/right button to disable or enable firewall. The rules iptables (see /usr/lib/enigma2/python/Plugins/Extensions/xModem/5iptables-rules_up & 5iptables-rules_down) swill reject all INCOMING connections from the ppp0 interface, thus making your receiver invisible on the Internet.'),
         ('File /etc/ppp/peers/', 'Use number buttons on your remote control to set peers file.\nAllowed only filename of the files located into /etc/ppp/peers directory.')]

    def newConfig(self):
        cur = self['config'].getCurrent()
        if cur == self.standard:
            self.initConfig()
            self.setStatus()
        elif cur == self.extopt:
            self.initConfig()
        elif cur == self.numbers:
            self.initConfig()
        elif cur == self.useums:
            self.initConfig()
        elif cur == self.altdns:
            self.initConfig()
        elif cur == self.autostart:
            self.initConfig()
        elif cur == self.adv_options:
            self.initConfig()
        elif cur == self.autorestart:
            self.initConfig()

    def setStatus(self):
        if not config.plugins.xModem.showhints.value:
            return
        try:
            cur = self['config'].getCurrent()[0]
        except TypeError:
            cur = None
        if self.currentcolor != self.statuscolors[0]:
            self.currentcolor = self.statuscolors[0]
            self['status'].instance.setForegroundColor(self.currentcolor)
        if cur is not None:
            for x in self.hints:
                if cur == _(x[0]):
                    extended_text = len(x) > 2 and _(x[2]) or ""
                    self['status'].setText(_(x[1]) + extended_text)
                    break
        else:
            self['status'].setText('')

    def handleInputHelpers(self):
		if self.green_function == CONNECT:
			if self["config"].getCurrent() is not None:
				if isinstance(self["config"].getCurrent()[1], ConfigText) or isinstance(self["config"].getCurrent()[1], ConfigPassword):
					self['TvIcon'].boolean = True
				else:
					self["TvIcon"].boolean = False
			else:
				self["TvIcon"].boolean = False
		else:
			self["TvIcon"].boolean = False

    def openVK(self):
		if self.green_function == CONNECT:
			if self["config"].getCurrent() is not None:
				if isinstance(self["config"].getCurrent()[1], ConfigText) or isinstance(self["config"].getCurrent()[1], ConfigPassword):
					from Screens.VirtualKeyBoard import VirtualKeyBoard
					self.session.openWithCallback(self.VirtualKeyBoardCallback, VirtualKeyBoard, title = self["config"].getCurrent()[0], text = self["config"].getCurrent()[1].getValue())

    def VirtualKeyBoardCallback(self, callback = None):
		cur = self["config"].getCurrent()
		if cur is None: return
		if callback is not None and len(callback):
			stop = False
			if cur[1] == config.plugins.xModem.imod.number:
				for x in callback:
					if x not in ('0','1','2','3','4','5','6','7','8','9','P','T','W','@'):
						stop = True
						break
			elif cur[1] == config.plugins.xModem.imod.port or cur[1] == config.plugins.xModem.gprs.port or cur[1] == config.plugins.xModem.cdma.port:
				for x in callback:
					if x not in ('0','1','2','3','4','5','6','7','8','9','a','b','c','d','e','m','s','t','u','v','y','A','B','C','M','S','T','U','/'):
						stop = True
						break
			elif cur[1] == config.plugins.xModem.gprs.vendid or cur[1] == config.plugins.xModem.gprs.prodid or cur[1] == config.plugins.xModem.cdma.vendid or cur[1] == config.plugins.xModem.cdma.prodid or cur[1] == config.plugins.xModem.peer.vendid or cur[1] == config.plugins.xModem.peer.prodid:
				for x in callback:
					if x not in ('0','1','2','3','4','5','6','7','8','9','a','b','c','d','e','f'):
						stop = True
						break
			if not stop:
				cur[1].setValue(callback)
				self["config"].invalidate(cur)

    def openMenu(self):
		global plugin_version
		text = _("Please select the necessary option...")
		menu = [(_("Show APN list"), "apn"), (_("Run command 'lsusb'"), "lsusb"), (_("Run command 'dmesg'"), "dmesg"), (_("Use 'usb_modeswitch --help' command"), "usb_modeswitch")]
		if self.green_function == CONNECT:
			# TODO
			#menu.append((_("Request USSD"), "ussd"))
			menu.append((_("Install ppp drivers from feed"), "drivers"))
			if config.plugins.xModem.standard.value == '1':
				if fileExists('/usr/bin/picocom') or fileExists('/usr/sbin/picocom'):
					menu.append((_("Instruction for utility 'picocom'"), "picocom"))
		elif self.red_function == DISCONNECT:
			if fileExists('/usr/sbin/pppstats')or fileExists('/usr/bin/pppstats'):
				menu.append((_("Run utility 'pppstats'"), "pppstats"))
		menu.append((_("About plugin"), "about"))
		def extraAction(choice):
			if choice:
				if choice[1] == "apn":
					self.session.open(myConsole,_("Show APN list"),["cat /usr/lib/enigma2/python/Plugins/Extensions/xModem/apnlist"])
				elif choice[1] == "lsusb":
					self.session.open(myConsole,_("Run command 'lsusb'"),["lsusb"])
				elif choice[1] == "dmesg":
					self.session.open(myConsole,_("Run command 'dmesg'"),["dmesg"])
				elif choice[1] == "usb_modeswitch":
					self.session.open(myConsole,_("usb_modeswitch --help"),["usb_modeswitch --help && cat /etc/list_modem.txt"])
				elif choice[1] == "drivers":
					self.install()
				elif choice[1] == "ussd":
					from requestUSSD import requestUSSDsetup
					self.session.open(requestUSSDsetup)
				elif choice[1] == "picocom":
					self.session.open(dataConsole,_("Instruction for utility 'picocom'"),["cat /usr/lib/enigma2/python/Plugins/Extensions/xModem/picocomlist && picocom -h"])
				elif choice[1] == "pppstats":
					self.session.open(dataConsole,_("Run utility 'pppstats'"),["pppstats -w1"])
				elif choice[1] == "about":
					self.session.open( MessageBox, _("Plugin version: %s\n\n") % plugin_version + _("Original developer and author code (2010):\nvlamo\nFurther development (2012-2015):\nDimitrij\n"), MessageBox.TYPE_INFO)
		dlg = self.session.openWithCallback(extraAction, ChoiceBox, title=text, list=menu)
		dlg.setTitle(_("Extra menu"))

    def getListCount(self):
        c = 0
        for x in self['config'].list:
            c += 1
        return c

    def keyLeft(self):
        if self.green_function == CONNECT:
            ConfigListScreen.keyLeft(self)
            self.newConfig()

    def keyRight(self):
        if self.green_function == CONNECT:
            ConfigListScreen.keyRight(self)
            self.newConfig()

    def keyUp(self):
        if self.green_function == CONNECT:
            idx = self['config'].getCurrentIndex()
            if idx <= 0:
                idx = self.getListCount()
            self['config'].setCurrentIndex(idx - 1)
            self.setStatus()
            self.handleInputHelpers()

    def keyDown(self):
        if self.green_function == CONNECT:
            idx = self['config'].getCurrentIndex()
            if idx >= self.getListCount() - 1:
                idx = -1
            self['config'].setCurrentIndex(idx + 1)
            self.setStatus()
            self.handleInputHelpers()

    def keyNumber(self, number):
        if self.green_function == CONNECT:
            ConfigListScreen.keyNumberGlobal(number)

    def deleteForward(self):
        if self.green_function == CONNECT:
            ConfigListScreen.keyDelete(self)

    def deleteBackward(self):
        if self.green_function == CONNECT:
            ConfigListScreen.keyBackspace(self)

    def install(self):
        if self.green_function == CONNECT:
            mbox = self.session.openWithCallback(self.installConfirmed, MessageBox, _("Do you really want to install the driver from the internet?"), MessageBox.TYPE_YESNO, default = False)
            mbox.setTitle(_("Install drivers for PPP"))

    def installConfirmed(self, answer):
        if answer:
            if fileExists('/usr/lib/enigma2/python/Plugins/Extensions/xModem/ppp_loader.sh'):
                system('chmod 755 /usr/lib/enigma2/python/Plugins/Extensions/xModem/ppp_loader.sh')
                self.session.open(myConsole, title = _("Please wait, install drivers..."), cmdlist = ["sh '/usr/lib/enigma2/python/Plugins/Extensions/xModem/ppp_loader.sh'"])

    def showInfo(self):
        if self.red_function == DISCONNECT:
            self.session.open(ConnectInfo, constarttime=starttime, iface=self.connectiface)

    def showLog(self):
        if fileExists('/etc/ppp/xmodem-connect.log'):
            self.session.open(LogConsole, _('xModem Connection Log...'), '/etc/ppp/xmodem-connect.log')

    def showHints(self):
        if self.green_function == CONNECT:
            config.plugins.xModem.showhints.value = not config.plugins.xModem.showhints.value
            config.plugins.xModem.showhints.save()
            if config.plugins.xModem.showhints.value == True:
                self.initHints()
                self.setStatus()
            else:
                self['status'].setText('')
                self.hints = []

    def __layoutFinished(self):
        if config.plugins.xModem.showhints.value:
            self.initHints()
        if conn.running():
            self.currentcolor = self.statuscolors[1]
            self['status'].instance.setForegroundColor(self.currentcolor)
            if connected:
                self['status'].setText(_('Connected!'))
                self.green_function = NONE
                self.red_function = DISCONNECT
            else:
                if dialstate == DIALING:
                    tmp = _('Dialing:')
                elif dialstate == LOGGING:
                    tmp = _('Dialing:') + self.dots + 'OK\n' + _('Login:')
                elif dialstate == CONNECTING:
                    tmp = _('Dialing:') + self.dots + 'OK\n' + _('Login:') + self.dots + 'OK\n'
                else:
                    tmp = ''
                self.dot = 0
                self['status'].setText(tmp)
                self.stateTimer.start(1000, False)
                self.green_function = NONE
                self.red_function = ABORT
        else:
            self.green_function = CONNECT
            self.red_function = NONE
            self.currentcolor = self.statuscolors[0]
            self['status'].instance.setForegroundColor(self.currentcolor)
            self.setStatus()
        self.updateGui()
        self.handleInputHelpers()

    def __closed(self):
        conn.appClosed.remove(self.pppdClosed)
        conn.dataAvail.append(dataAvail)
        conn.dataAvail.remove(self.dataAvail)
        if logfd != -1:
            logfd.flush()
        if not connected:
            conn.sendCtrlC()

    def setExamplesCommands(self):
		if self.green_function == CONNECT:
			text = _("Set AT-command as:")
			menu = [(_("Init string"), "init"), (_("Deinit string"), "deinit")]
			def extraAction(choice):
				if choice:
					if choice[1] == "init":
						if config.plugins.xModem.standard.value == '0':
							config.plugins.xModem.imod.initstr.value = config.plugins.xModem.examples_commands.value
						elif config.plugins.xModem.standard.value == '1':
							config.plugins.xModem.gprs.initstr.value = config.plugins.xModem.examples_commands.value
					elif choice[1] == "deinit":
						if config.plugins.xModem.standard.value == '0':
							config.plugins.xModem.imod.deinstr.value = config.plugins.xModem.examples_commands.value
						elif config.plugins.xModem.standard.value == '1':
							config.plugins.xModem.gprs.deinstr.value = config.plugins.xModem.examples_commands.value
					self.initConfig()
			dlg = self.session.openWithCallback(extraAction, ChoiceBox, title=text, list=menu)
			dlg.setTitle(_("AT-commands"))

    def keyOK(self, answer = None):
		if self.green_function == CONNECT and self["config"].getCurrent() is not None and self["config"].getCurrent()[1] == config.plugins.xModem.examples_commands:
			self.setExamplesCommands()
			return
		if answer is None:
			if self["config"].isChanged():
				self.session.openWithCallback(self.keyOK, MessageBox, _("Really saving settings and close?"))
			else:
				self.close()
		elif answer:
			if self.prev_extmenu != config.plugins.xModem.extmenu.value:
				plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
			self.setRestartSoftcamFile()
			self.setIptablesFiles()
			if not config.plugins.xModem.autorun.value:
				config.plugins.xModem.autorestart_modem.value = "0"
			for x in self['config'].list:
				x[1].save()
			if self.red_function == DISCONNECT:
				if self.autorestart_modem != config.plugins.xModem.autorestart_modem.value:
					global autorestartModem
					if autorestartModem is not None:
						if config.plugins.xModem.autorestart_modem.value != "0":
							autorestartModem.stop()
							autorestartModem.start()
						else:
							autorestartModem.stop()
			self.close()

    def setIptablesFiles(self):
		if config.plugins.xModem.iptables.value:
			iptables = True
			if fileExists('/usr/lib/enigma2/python/Plugins/Extensions/xModem/5iptables-rules_up'):
				system("cp /usr/lib/enigma2/python/Plugins/Extensions/xModem/5iptables-rules_up /etc/ppp/ip-up.d/5iptables-rules_up")
				if fileExists('/etc/ppp/ip-up.d/5iptables-rules_up'):
					chmod("/etc/ppp/ip-up.d/5iptables-rules_up", 0755)
				else:
					iptables = False
			else:
				iptables = False
			if fileExists('/usr/lib/enigma2/python/Plugins/Extensions/xModem/5iptables-rules_down'):
				system("cp /usr/lib/enigma2/python/Plugins/Extensions/xModem/5iptables-rules_down /etc/ppp/ip-up.down/5iptables-rules_down")
				if fileExists('/etc/ppp/ip-down.d/5iptables-rules_down'):
					chmod("/etc/ppp/ip-up.down/5iptables-rules_down", 0755)
				else:
					iptables = False
			else:
				iptables = False
			if not iptables:
				config.plugins.xModem.iptables.value = False
		else:
			if fileExists("/etc/ppp/ip-up.d/5iptables-rules_up"):
				system("rm -rf /etc/ppp/ip-up.d/5iptables-rules_up")
			if fileExists("/etc/ppp/ip-up.down/5iptables-rules_down"):
				system("rm -rf /etc/ppp/ip-down.d/5iptables-rules_down")

    def setRestartSoftcamFile(self):
		if config.plugins.xModem.restart_softcam.value:
			if fileExists('/usr/lib/enigma2/python/Plugins/Extensions/xModem/10user_emurestart'):
				system("cp /usr/lib/enigma2/python/Plugins/Extensions/xModem/10user_emurestart /etc/ppp/ip-up.d/10user_emurestart")
				if fileExists('/etc/ppp/ip-up.d/10user_emurestart'):
					chmod("/etc/ppp/ip-up.d/10user_emurestart", 0755)
				else:
					config.plugins.xModem.restart_softcam.value = False
			elif fileExists("/usr/lib/enigma2/python/Plugins/Extensions/xModem/10emurestart"):
				system("cp /usr/lib/enigma2/python/Plugins/Extensions/xModem/10emurestart /etc/ppp/ip-up.d/10emurestart")
				if fileExists('/etc/ppp/ip-up.d/10emurestart'):
					chmod("/etc/ppp/ip-up.d/10emurestart", 0755)
				else:
					config.plugins.xModem.restart_softcam.value = False
			else:
				config.plugins.xModem.restart_softcam.value = False
		else:
			if fileExists("/etc/ppp/ip-up.d/10user_emurestart"):
				system("rm -rf /etc/ppp/ip-up.d/10user_emurestart")
			elif fileExists("/etc/ppp/ip-up.d/10emurestart"):
				system("rm -rf /etc/ppp/ip-up.d/10emurestart")

    def keyExit(self, answer = None):
		if answer is None:
			if self["config"].isChanged():
				self.session.openWithCallback(self.keyExit, MessageBox, _("Really close without saving settings?"))
			else:
				self.close()
		elif answer:
			for x in self["config"].list:
				x[1].cancel()
			self.close()

    def stateLoop(self):
        txt = self['status'].getText()
        if self.dot > 7:
            txt = txt[:-7]
            self.dot = 1
        else:
            txt += '.'
            self.dot += 1
        #if self.green_function == CONNECT:
        #    txt = ''
        self['status'].setText(txt)

    def connect(self):
        if self.green_function == CONNECT:
            self.connectiface = None
            self.dot = 0
            self.currentcolor = self.statuscolors[1]
            self['status'].instance.setForegroundColor(self.currentcolor)
            self['status'].setText(_('Dialing:'))
            self.stateTimer.start(1000, False)
            ret = StartConnect()
            if ret:
                self.pppdClosed(ret)
                pppdClosed(ret)
            self.green_function = NONE
            self.red_function = ABORT
            self.updateGui()

    def disconnect(self):
        conn.sendCtrlC()
        self.red_function = NONE
        self.updateGui()
        if autorestartModem:
            autorestartModem.timer.stop()

    def pppdClosed(self, retval):
        global connected
        global starttime
        self.stateTimer.stop()
        self.red_function = NONE
        self.green_function = CONNECT
        if connected:
            self['status'].setText(_('Connection terminated.'))
        self.updateGui()
        connected = False
        starttime = None

    def dataAvail(self, text):
        global connected
        global starttime
        tmp = text
        writeLog(tmp)
        if text.find('unrecognized option') != -1:
            pos = text.find('unrecognized option')
            tmp1 = 'pppd: ' + text[pos:]
            tmp1 = tmp1[:tmp1.find('\n') + 1]
            tmp = self['status'].getText()
            tmp += self.dots + _('FAILED') + '\n'
            tmp += tmp1
            self['status'].setText(tmp)
        if text.find('Serial connection established') != -1:
            tmp = self['status'].getText()
            dots = self.dots[:-self.dot]
            tmp += dots + 'OK\n' + _('Login:')
            self.dot = 0
            self['status'].setText(tmp)
        if text.find('Using interface') != -1:
            pos = text.find('Using interface')
            length = len('Using interface ')
            tmp = text[pos + length:]
            self.connectiface = tmp[:4]
        if text.find('AP authentication succeeded') != -1 or text.find('No auth is possible') != -1:
            tmp = self['status'].getText()
            dots = self.dots[:-self.dot]
            tmp += dots + 'OK\n'
            self.dot = 0
            self['status'].setText(tmp)
            self.stateTimer.stop()
        if text.find('ip-up finished') != -1:
            self.stateTimer.stop()
            if starttime == None:
                starttime = getUptime()
            if config.plugins.xModem.altdns.value:
                setAltDNS()
            tmp = self['status'].getText()
            tmp += _('Connected :)') + '\n'
            self['status'].setText(tmp)
            self.red_function = DISCONNECT
            connected = True
        if text.find('Connect script failed') != -1:
            tmp = self['status'].getText()
            dots = self.dots[:-self.dot]
            tmp += dots + _('FAILED') + '\n'
            self['status'].setText(tmp)
            self.stateTimer.stop()
            self.red_function = NONE
            self.green_function = CONNECT
            self.disconnect()
        self.updateGui()

    def updateGui(self):
        if self.red_function == NONE:
            self['key_red'].setText('')
        elif self.red_function == DISCONNECT:
            self['key_red'].setText(_('Disconnect'))
            self['key_yellow'].setText(_("Statistics"))
        elif self.red_function == ABORT:
            self['key_red'].setText(_('Abort'))
        if self.green_function == NONE:
            self['key_green'].setText('')
        elif self.green_function == CONNECT:
            self['key_green'].setText(_('Connect'))
            self['key_yellow'].setText('')
        self['key_blue'].setText(_("Save/OK"))
        self['InfoIcon'].boolean = self.red_function == DISCONNECT
        self['TextIcon'].boolean = fileExists('/etc/ppp/xmodem-connect.log')
        focus_enabled = self.green_function == CONNECT
        self['config'].instance.setSelectionEnable(focus_enabled)
        self['ListActions'].setEnabled(not focus_enabled)

def autostart(reason, **kwargs):
	if reason == 0:
		global run_autostart
		if run_autostart is None:
			run_autostart = StartConnect(True)
	elif reason == 1:
		StopConnect(True)

def main(session, **kwargs):
	session.open(ModemSetup)

def menu(menuid, **kwargs):
	if menuid == "mainmenu" and config.plugins.xModem.mainmenu.value:
		return [(_("xModem"), main, "x_modem", 45)]
	return []

def Plugins(**kwargs):
	if config.plugins.xModem.extmenu.value:
		return [PluginDescriptor(where=PluginDescriptor.WHERE_AUTOSTART, fnc=autostart),
			PluginDescriptor(name=_('xModem'), description=_('plugin to connect to internet'), where=PluginDescriptor.WHERE_PLUGINMENU, icon='xmodem.png', fnc=main),
			PluginDescriptor(name=_('xModem'), description=_('plugin to connect to internet'), where=PluginDescriptor.WHERE_EXTENSIONSMENU, icon='xmodem.png', fnc=main),
			PluginDescriptor(name=_('xModem'), description=_('plugin to connect to internet'), where=PluginDescriptor.WHERE_MENU, fnc=menu)]
	else:
		return [PluginDescriptor(where=PluginDescriptor.WHERE_AUTOSTART, fnc=autostart), PluginDescriptor(name=_('xModem'), description=_('plugin to connect to internet'), where=PluginDescriptor.WHERE_PLUGINMENU, icon='xmodem.png', fnc=main),PluginDescriptor(name=_('xModem'), description=_('plugin to connect to internet'), where=PluginDescriptor.WHERE_MAINMENU, fnc=menu) ]