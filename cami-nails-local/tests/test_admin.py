import sqlite3,unittest
from pathlib import Path
from werkzeug.security import check_password_hash
import test_app
from limpar_dados import reset_data
class AdminTest(unittest.TestCase):
 setUp=test_app.StudioTest.setUp
 tearDown=test_app.StudioTest.tearDown
 post=test_app.StudioTest.post
 login=test_app.StudioTest.login
 def test_change_credentials_and_revoke_sessions(self):
  self.login();other=self.app.test_client();other.get('/login')
  with other.session_transaction() as s:token=s['csrf']
  other.post('/login',data={'csrf':token,'email':'teste@example.com','senha':'senha-de-teste-123'})
  r=self.post('/administracao',{'email':'camila@example.com','senha_atual':'senha-de-teste-123','nova_senha':'nova-senha-teste-123','confirmacao':'nova-senha-teste-123'})
  self.assertEqual(r.status_code,200);self.assertEqual(other.get('/clientes').status_code,302)
  with sqlite3.connect(self.path) as c:
   email,hashed,version=c.execute('SELECT email,senha,versao_sessao FROM usuarios').fetchone()
  self.assertEqual(email,'camila@example.com');self.assertTrue(check_password_hash(hashed,'nova-senha-teste-123'));self.assertEqual(version,2)
 def test_wrong_password_does_not_change_account(self):
  self.login();r=self.post('/administracao',{'email':'errado@example.com','senha_atual':'errada'})
  self.assertEqual(r.status_code,422)
  with sqlite3.connect(self.path) as c:self.assertEqual(c.execute('SELECT email FROM usuarios').fetchone()[0],'teste@example.com')
 def test_reset_auth_backup_and_preservation(self):
  self.login();self.post('/clientes/novo',{'nome':'Teste Limpeza','telefone':'41999991111'})
  self.post('/agenda/novo',{'cliente_id':'1','servico_id':'1','inicio':'2026-10-18T09:00','status':'Concluído'})
  dest=Path(self.tmp.name)/'backups'
  with self.assertRaises(ValueError):reset_data(self.path,dest,'teste@example.com','errada')
  with sqlite3.connect(self.path) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM clientes').fetchone()[0],1)
  saved=reset_data(self.path,dest,'teste@example.com','senha-de-teste-123')
  with sqlite3.connect(saved) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM clientes').fetchone()[0],1)
  with sqlite3.connect(self.path) as c:
   for table in ['clientes','agendamentos','registros','mensagens','envios_manuais','financeiro']:
    self.assertEqual(c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)
   self.assertEqual(c.execute('SELECT COUNT(*) FROM usuarios').fetchone()[0],1)
   self.assertEqual(c.execute('SELECT COUNT(*) FROM servicos').fetchone()[0],4)
   self.assertEqual(c.execute('SELECT COUNT(*) FROM modelos').fetchone()[0],2)
  self.assertEqual(self.client.get('/clientes').status_code,302)
