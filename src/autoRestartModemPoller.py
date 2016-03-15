from __init__ import _
from Components.config import config
from plugin import StartConnect, StopConnect, conn
from enigma import eTimer
from Screens.MessageBox import MessageBox
import Screens.InfoBar
import Screens.Standby
from Tools import Notifications

class autoRestartModemPoller:
	"""Automatically restarting xModem"""
	def __init__(self):
		self.timer = eTimer()
		self.wait_timer = eTimer()
		self.wait_timer.callback.append(self.setPoll)

	def start(self):
		if not self.timer.callback:
			self.timer.callback.append(self.runPoll)
		if not self.wait_timer.callback:
			self.wait_timer.callback.append(self.setPoll)
		if config.plugins.xModem.autorestart_modem.value != "0":
			if self.timer.isActive():
				self.timer.stop()
			print "[autoRestartModemPoller] add poll modem"
			self.timer.startLongTimer(int(config.plugins.xModem.autorestart_modem.value) * 60)

	def stop(self):
		self.timer.stop()
		self.wait_timer.stop()
		if self.timer.callback:
			self.timer.callback.remove(self.runPoll)
		if not self.wait_timer.callback:
			self.wait_timer.callback.remove(self.setPoll)
		print "[autoRestartModemPoller] remove poll modem"

	def runPoll(self):
		if config.plugins.xModem.autorestart_modem.value != "0":
			notify = config.plugins.xModem.show_message.value and not Screens.Standby.inStandby and Screens.InfoBar.InfoBar.instance and Screens.InfoBar.InfoBar.instance.execing
			if notify:
				Notifications.AddPopup(text = _("Forced auto restarting modem!\nPlease wait..."), type = MessageBox.TYPE_INFO, timeout = 15)
			StopConnect(True)
			conn.sendCtrlC()
			print "[autoRestartModemPoller] stop modem"
			if self.wait_timer.isActive():
				self.wait_timer.stop()
			self.wait_timer.startLongTimer(15)
		else:
			self.timer.stop()

	def setPoll(self):
			if self.timer.isActive():
				self.timer.stop()
			ret = StartConnect(True)
			print "[autoRestartModemPoller] run start modem"
			if not ret:
				self.timer.startLongTimer(int(config.plugins.xModem.autorestart_modem.value) * 60)
				print "[autoRestartModemPoller] modem now enabled, next restart after:", int(config.plugins.xModem.autorestart_modem.value) * 60
			else:
				notify = config.plugins.xModem.show_message.value and not Screens.Standby.inStandby and Screens.InfoBar.InfoBar.instance and Screens.InfoBar.InfoBar.instance.execing
				if notify:
					Notifications.AddPopup(text = _("Failed start modem!\nPlease run modem manually..."), type = MessageBox.TYPE_INFO, timeout = 10)
				print "[autoRestartModemPoller] failed start modem"
				#StopConnect()

