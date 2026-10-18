import sqlite3
from datetime import datetime
import test_app
from app import create_app, SCHEMA
from app.agenda import prepare_queue
class AgendaTest(test_app.StudioTest):
 def client_seed(self):
  self.login();self.post('/clientes/novo',{'nome':'Camila Teste','telefone':'41912345678','cep':'80000-000','logradouro':'Rua Teste','numero':'10','bairro':'Centro','cidade':'Curitiba','uf':'pr','aceita_mensagens':'1'})
 def appointment(self,start='2026-11-01T10:00',**extra):
  return dict(cliente_id='1',servico_id='1',inicio=start,status='Agendado',observacoes='',**extra)
 def test_address_and_format(self):
  self.client_seed();r=self.client.get('/clientes/1');self.assertIn(b'(41) 91234-5678',r.data);self.assertIn(b'Rua Teste',r.data)
  for url in ['/agenda','/agenda?visao=mes','/agenda?visao=dia','/agenda/novo?cliente=1','/mensagens']:
   self.assertEqual(self.client.get(url).status_code,200,url)
 def test_schedule_conflict_history_and_cancel(self):
  self.client_seed();self.assertEqual(self.post('/agenda/novo',self.appointment()).status_code,200)
  self.assertEqual(self.post('/agenda/novo',self.appointment('2026-11-01T11:00')).status_code,422)
  self.assertEqual(self.post('/agenda/novo',self.appointment('2026-11-01T12:00')).status_code,200)
  with sqlite3.connect(self.path) as c: c.execute('UPDATE servicos SET preco=20000 WHERE id=1')
  self.post('/agenda/1/editar',self.appointment())
  with sqlite3.connect(self.path) as c: self.assertEqual(c.execute('SELECT preco FROM agendamentos WHERE id=1').fetchone()[0],10000)
  d=self.appointment();d['status']='Cancelado';self.post('/agenda/1/editar',d)
  self.assertEqual(self.post('/agenda/novo',self.appointment()).status_code,200)
  self.assertIn(b'Alongamento Molde F1',self.client.get('/clientes/1').data)
 def test_migration_preserves_v1(self):
  path=self.path.parent/'old.sqlite3'
  with sqlite3.connect(path) as c:
   c.executescript(SCHEMA);c.execute("INSERT INTO clientes(nome,telefone) VALUES('Cliente Antiga','41999991111')")
  create_app({'TESTING':True,'DATABASE':str(path)})
  with sqlite3.connect(path) as c:
   self.assertEqual(c.execute('SELECT nome,cep FROM clientes').fetchone(),('Cliente Antiga',''))
   self.assertTrue(path.with_suffix('.antes-etapa2.sqlite3').exists())
  create_app({'TESTING':True,'DATABASE':str(path)})
  with sqlite3.connect(path) as c: self.assertEqual(c.execute('SELECT COUNT(*) FROM modelos').fetchone()[0],2)


 def test_manual_messages_no_time_window(self):
  from unittest.mock import patch
  self.client_seed();self.post('/agenda/novo',self.appointment('2026-11-10T10:00'))
  self.post('/mensagens/modelo/novo',{'nome':'Confirmar presença','texto':'Oi, {nome}! {servico} em {data} às {hora}.'})
  with sqlite3.connect(self.path) as c:
   mid=c.execute("SELECT id FROM modelos WHERE nome='Confirmar presença'").fetchone()[0]
   c.execute('UPDATE clientes SET aceita_mensagens=0 WHERE id=1')
  with patch('app.agenda.now',return_value=datetime(2026,11,1,9)):
   response=self.client.get(f'/mensagens?agendamento=1&modelo={mid}')
   self.assertEqual(response.status_code,200)
   self.assertIn('10/11/2026',response.get_data(as_text=True))
   self.assertNotIn('Antecedência',response.get_data(as_text=True))
   self.assertIn('Camila Teste',response.get_data(as_text=True))
   response=self.post('/mensagens/abrir',{'agendamento':'1','modelo':str(mid),'revisao':'1','telefone':'41912345678','texto':'Olá! Teste revisado.'})
   self.assertEqual(response.status_code,200)
   self.assertIn('https://wa.me/5541912345678',response.get_data(as_text=True))
   self.assertNotIn('Location',response.headers)
   self.assertIn("form-action 'self'",response.headers['Content-Security-Policy'])
  with sqlite3.connect(self.path) as c:
   self.assertEqual(c.execute('SELECT texto FROM envios_manuais').fetchone()[0],'Olá! Teste revisado.')
 def test_stale_manual_message_and_invalid_model(self):
  from unittest.mock import patch
  self.client_seed();self.post('/agenda/novo',self.appointment())
  with patch('app.agenda.now',return_value=datetime(2026,11,1,9)):
   response=self.post('/mensagens/abrir',{'agendamento':'1','modelo':'1','revisao':'99','telefone':'41912345678','texto':'Teste'})
   self.assertIn('mudou',response.get_data(as_text=True))
  self.post('/mensagens/modelo/novo',{'nome':'Modelo inválido','texto':'{desconhecido}'})
  with sqlite3.connect(self.path) as c:
   self.assertEqual(c.execute('SELECT COUNT(*) FROM envios_manuais').fetchone()[0],0)
   self.assertEqual(c.execute("SELECT COUNT(*) FROM modelos WHERE nome='Modelo inválido'").fetchone()[0],0)
 def test_calendar_slots_and_prefilled_time(self):
  self.client_seed();self.post('/agenda/novo',self.appointment())
  r=self.client.get('/agenda?data=2026-11-01&visao=semana')
  self.assertIn('data-minute="600"',r.get_data(as_text=True))
  self.assertIn('data-duration="120"',r.get_data(as_text=True))
  r=self.client.get('/agenda/novo?data=2026-11-01&hora=14:30')
  self.assertIn('2026-11-01T14:30',r.get_data(as_text=True))
  r=self.client.get('/agenda?data=2026-11-01&visao=mes')
  self.assertIn('month-grid',r.get_data(as_text=True))
