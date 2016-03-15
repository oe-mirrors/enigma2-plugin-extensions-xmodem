from distutils.core import setup
import setup_translate


setup(name = 'enigma2-plugin-extensions-xmodem',
		version='1.4',
		author='Vlamo/Dimitrij',
		author_email='dima-73@inbox.lv',
		package_dir = {'Extensions.xModem': 'src'},
		packages=['Extensions.xModem'],
		package_data={'Extensions.xModem': ['*.png', '*.xml', 'picocomlist', 'apnlist', '10emurestart', '5iptables-rules_up', '5iptables-rules_down', 'ppp_loader.sh', 'images/*.png']},
		description = 'plugin to connect to internet via any modems',
		cmdclass = setup_translate.cmdclass,
	)

