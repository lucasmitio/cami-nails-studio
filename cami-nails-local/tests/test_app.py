import tempfile, unittest, sqlite3
from pathlib import Path
from app import create_app
from werkzeug.security import generate_password_hash
import backup
class StudioTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'test.sqlite3';self.app=create_app({'TESTING':True,'DATABASE':str(self.path),'SECRET_KEY':'testing-only'})
  self.assertEqual(self.app.test_cli_runner().invoke(args=['init-db']).exit_code,0)
  with sqlite3.connect(self.path) as c: c.execute('INSERT INTO usuarios(email,senha) VALUES(?,?)',('teste@example.com',generate_password_hash('senha-de-teste-123')))
  self.client=self.app.test_client()
 def tearDown(self): self.tmp.cleanup()
 def post(self,path,data):
  self.client.get('/login')
  with self.client.session_transaction() as s: data['csrf']=s['csrf']
  return self.client.post(path,data=data,follow_redirects=True)
 def login(self): self.post('/login',{'email':'teste@example.com','senha':'senha-de-teste-123'})
 def test_protection(self):
  for route in ['/','/clientes','/servicos','/clientes/novo']: self.assertEqual(self.client.get(route).status_code,302)
  self.assertEqual(self.client.post('/clientes/novo',data={'nome':'Teste'}).status_code,400)
  self.login();self.assertEqual(self.client.get('/').status_code,200)
  self.post('/sair',{});self.assertEqual(self.client.get('/clientes').status_code,302)
 def test_client_persistence_duplicate_and_inactivation(self):
  self.login();data={'nome':'Cliente Teste','telefone':'(41) 99999-1234','nascimento':'2000-01-01','instagram':'@teste','observacoes':'<script>alert(1)</script>'}
  r=self.post('/clientes/novo',data.copy());self.assertEqual(r.status_code,200);self.assertIn(b'&lt;script&gt;',r.data)
  self.assertEqual(self.post('/clientes/novo',data.copy()).status_code,422)
  data['nome']='Nome Atualizado';self.assertEqual(self.post('/clientes/1/editar',data.copy()).status_code,200);self.post('/clientes/1/status',{})
  with sqlite3.connect(self.path) as c: self.assertEqual(c.execute('SELECT nome,ativo FROM clientes').fetchone(),('Nome Atualizado',0))
  self.assertIn(b'Nome Atualizado',self.client.get('/clientes?status=inativos&q=99999').data)
 def test_services_validation_and_money(self):
  self.login();data={'nome':'Serviço Teste','preco':'80,25','duracao':'90','intervalo':'21','descricao':'Teste'}
  self.assertEqual(self.post('/servicos/novo',data.copy()).status_code,200)
  data['preco']='NaN';self.assertEqual(self.post('/servicos/novo',data.copy()).status_code,422)
  with sqlite3.connect(self.path) as c: self.assertEqual(c.execute("SELECT preco FROM servicos WHERE nome='Serviço Teste'").fetchone()[0],8025)
 def test_backup_restore(self):
  backup.DB=self.path;dest=Path(self.tmp.name)/'backup.sqlite3';backup.backup(dest)
  with sqlite3.connect(self.path) as c: c.execute('DELETE FROM servicos')
  with sqlite3.connect(dest) as source,sqlite3.connect(self.path) as target: source.backup(target)
  backup.validate(self.path)
  with sqlite3.connect(self.path) as c: self.assertEqual(c.execute('SELECT COUNT(*) FROM servicos').fetchone()[0],4)
 def test_login_throttling(self):
  for _ in range(5): self.assertEqual(self.post('/login',{'email':'errado','senha':'errada'}).status_code,401)
  self.assertEqual(self.post('/login',{'email':'errado','senha':'errada'}).status_code,429)
if __name__=='__main__': unittest.main()
