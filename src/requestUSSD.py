from __init__ import _
from Components.ActionMap import ActionMap
from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigSelection, getConfigListEntry, ConfigText
from Screens.MessageBox import MessageBox
from Components.Button import Button
from Components.Label import Label
from Tools.Directories import fileExists
import enigma
import base64

config.plugins.xModem.ussd = ConfigSubsection()
config.plugins.xModem.ussd.number = ConfigText('*100#', fixed_size=False)
config.plugins.xModem.ussd.number.setUseableChars(u'0123456789*#')
config.plugins.xModem.ussd.encoding = ConfigSelection([('0', 'a'),
 ('1', 'b'),
 ('2', 'c'),
 ('3', 'd')], default='0')
config.plugins.xModem.ussd.apn = ConfigText('internet', fixed_size=False)
config.plugins.xModem.ussd.port = ConfigText('/dev/ttyUSB0', fixed_size=False)
config.plugins.xModem.ussd.port.setUseableChars(u'0123456789abcdemstuvyABCMSTU/')

class requestUSSDsetup(Screen, ConfigListScreen):
	skin = """
		<screen position="center,center" size="510,320" title="Request USSD" >
			<widget name="config" position="5,5" size="500,190" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="180,200" zPosition="0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/red.png" position="5,200" zPosition="0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="360,200" zPosition="0" size="140,40" alphatest="on" />
			<widget name="save" position="360,200" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;17" transparent="1" backgroundColor="blue" />
			<widget name="ok" position="180,200" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;17" transparent="1" backgroundColor="green" />
			<widget name="cancel" position="5,200" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;17" transparent="1" backgroundColor="red" />
			<ePixmap pixmap="skin_default/div-v.png" position="0,250" size="510,2" zPosition="1" />
			<widget name="status" position="5,257" size="500,57" font="Regular;17" foregroundColor="#abcdef" />
		</screen>"""

	def __init__(self, session, args=None):
		self.skin = requestUSSDsetup.skin
		self.setup_title = _("Request USSD")
		Screen.__init__(self, session)
		self["ok"] = Button(_("Save setup"))
		self["cancel"] = Button(_("Cancel"))
		self["save"] = Button(_("Run/OK"))
		self['status'] = Label('')
		self["actions"] = ActionMap(["SetupActions", "ColorActions"], 
		{
			"ok": self.keyOk,
			"save": self.keyGreen,
			"cancel": self.keyRed,
			"blue": self.keyBlue,
		}, -2)
		ConfigListScreen.__init__(self, [])
		self.initConfig()
		self.createSetup()
		self.p = None
		self.onClose.append(self.__closed)
		self.onLayoutFinish.append(self.__layoutFinished)

	def __closed(self):
		pass

	def __layoutFinished(self):
		self.setTitle(self.setup_title)

	def initConfig(self):
		def getPrevValues(section):
			res = { }
			for (key,val) in section.content.items.items():
				if isinstance(val, ConfigSubsection):
					res[key] = getPrevValues(val)
				else:
					res[key] = val.value
			return res

		self.ussd = config.plugins.xModem.ussd
		self.prev_values = getPrevValues(self.ussd)
		self.cfg_apn = getConfigListEntry(_("APN"), self.ussd.apn)
		self.cfg_number = getConfigListEntry(_("Number"), self.ussd.number)
		self.cfg_port  = getConfigListEntry(_("Port"), self.ussd.port)
		self.cfg_encoding = getConfigListEntry(_("Encoding request"), self.ussd.encoding)


	def createSetup(self):
		list = [self.cfg_apn]
		list.append(self.cfg_number)
		list.append(self.cfg_port)
		list.append(self.cfg_encoding)
		self["config"].list = list
		self["config"].l.setList(list)

	def keyOk(self):
		self.keyBlue()

	def keyRed(self):
		def setPrevValues(section, values):
			for (key,val) in section.content.items.items():
				value = values.get(key, None)
				if value is not None:
					if isinstance(val, ConfigSubsection):
						setPrevValues(val, value)
					else:
						val.value = value
		setPrevValues(self.ussd, self.prev_values)
		self.keyGreen()

	def keyGreen(self): 
		self.ussd.save()
		self.close()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)

	def keyRight(self):
		ConfigListScreen.keyRight(self)

	def write2p(self, a):
		self.p.write(a + '\r\n')
		print 'Waiting answer...'
		self['status'].setText('Waiting answer...')
		l = self.p.readline()
		self.p.close()
		if l:
			for l in self.p:
				print l
				if l.startswith('+CUSD'):
					answer =  base64.b16decode(l[10:l.rfind('"')]).decode('utf-16-be')
					print answer
					self['status'].setText(answer)
					break

	def to7bit(self, src):
		result, count, last = [], 0, 0
		for c in src:
			this = ord(c) << (8 - count)
			if count:
				result.append('%02X' % ((last >> 8) | (this & 0xFF)))
			count = (count + 1) % 8
			last = this
		result.append('%02x' % (last >> 8))
		return ''.join(result)

	def keyBlue(self):
		self['status'].setText('')
		if fileExists(self.ussd.port.value):
			self.p = open('%s' % self.ussd.port.value, 'w+b')
			if self.p:
				self.write2p('AT+CUSD=1,' + self.to7bit(self.ussd.number.value) + ',15')
			else:
				self.p.close()
		else:
			self['status'].setText('port not found')
