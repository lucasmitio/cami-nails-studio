import importlib.machinery, importlib.util, unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import urllib.error
path=Path(__file__).resolve().parents[1]/'abrir_studio.pyw'
loader=importlib.machinery.SourceFileLoader('studio_launcher',str(path))
spec=importlib.util.spec_from_loader(loader.name,loader)
launcher=importlib.util.module_from_spec(spec);loader.exec_module(launcher)
class LauncherTest(unittest.TestCase):
 def test_detect_our_server(self):
  response=MagicMock();response.__enter__.return_value.read.return_value=(' {"app":"cami-nails","installation":"'+launcher.INSTALLATION+'"}').encode()
  with patch.object(launcher.urllib.request,'urlopen',return_value=response):self.assertEqual(launcher.server_state(),'ready')
 def test_detect_foreign_server(self):
  response=MagicMock();response.__enter__.return_value.read.return_value=b'{"app":"other"}'
  with patch.object(launcher.urllib.request,'urlopen',return_value=response):self.assertEqual(launcher.server_state(),'other')
 def test_offline(self):
  with patch.object(launcher.urllib.request,'urlopen',side_effect=urllib.error.URLError('refused')):self.assertEqual(launcher.server_state(),'offline')
