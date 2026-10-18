import sqlite3, secrets, unittest
from datetime import datetime,date
from unittest.mock import patch
import test_app
from app.financeiro import stats, period
from flask import g
class FinanceTest(unittest.TestCase):
 setUp=test_app.StudioTest.setUp
 tearDown=test_app.StudioTest.tearDown
 post=test_app.StudioTest.post
 login=test_app.StudioTest.login
 def seed(self):
  self.login();self.post('/clientes/novo',{'nome':'Cliente Teste','telefone':'41999991111'})
  self.post('/agenda/novo',{'cliente_id':'1','servico_id':'1','inicio':'2026-10-20T10:00','status':'Agendado'})
 def payment(self,amount='40.00',**changes):
  data=dict(tipo='Receita',valor=amount,data='2026-10-18',descricao='Sinal',categoria='Serviços',forma='Pix',agendamento_id='1',chave=secrets.token_hex(24));data.update(changes);return data
 def report(self,start=date(2026,10,1),end=date(2026,11,1),mode='mes'):
  with self.app.app_context():
   g.app_database=str(self.path);return stats(start,end,mode)

 def complete(self,status='Concluído',day='2026-10-20T10:00'):
  return self.post('/agenda/1/editar',{'cliente_id':'1','servico_id':'1','inicio':day,'status':status})
 def test_completion_counts_once_and_reopening_removes_revenue(self):
  self.seed();self.assertEqual(self.report()['income'],0)
  self.assertEqual(self.complete().status_code,200);self.assertEqual(self.report()['income'],10000)
  self.complete();self.assertEqual(self.report()['income'],10000)
  self.complete('Agendado');self.assertEqual(self.report()['income'],0)
  self.complete();self.assertEqual(self.report()['income'],10000)
  self.complete('Cancelado');self.assertEqual(self.report()['income'],0)
 def test_legacy_payment_not_double_counted_expenses_ignored(self):
  self.seed();self.complete()
  with sqlite3.connect(self.path) as c:
   for kind in ['Receita','Despesa']:
    c.execute("INSERT INTO financeiro(tipo,valor,data,descricao,categoria,forma,agendamento_id,usuario_id,chave,criado_em) VALUES(?,10000,'2026-10-18','Antigo','Outros','Pix',1,1,?,'2026-10-18')",(kind,kind))
  self.assertEqual(self.report()['income'],10000)
  r=self.client.get('/financeiro');html=r.get_data(as_text=True)
  self.assertNotIn('Despesas',html);self.assertNotIn('Saldo do período',html)
 def test_revenue_uses_appointment_date_and_historical_price(self):
  self.seed();self.complete(day='2026-09-30T10:00')
  self.assertEqual(self.report()['income'],0)
  self.assertEqual(self.report(date(2026,9,1),date(2026,10,1))['income'],10000)
  with sqlite3.connect(self.path) as c:c.execute('UPDATE servicos SET preco=20000 WHERE id=1')
  self.complete();self.assertEqual(self.report()['income'],10000)
 def test_filters_and_legacy_completed_records(self):
  self.seed()
  with sqlite3.connect(self.path) as c:c.execute("UPDATE agendamentos SET status='Concluído' WHERE id=1")
  self.assertEqual(self.report()['income'],10000)
  for mode in ['semana','mes','ano']:
   for path in ['/', '/financeiro']:
    self.assertEqual(self.client.get(f'{path}?periodo={mode}&data=2026-10-18').status_code,200)
   self.assertEqual(self.client.get(f'/agenda?visao={mode}&data=2026-10-18').status_code,200)
 def test_manual_entry_is_disabled(self):
  self.seed();self.post('/financeiro/novo',self.payment())
  with sqlite3.connect(self.path) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM financeiro').fetchone()[0],0)
