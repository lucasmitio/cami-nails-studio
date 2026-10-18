import re
import sqlite3
import unittest
from datetime import datetime
from unittest.mock import patch
import backup
import test_app

class RevisionTest(unittest.TestCase):
    setUp=test_app.StudioTest.setUp
    tearDown=test_app.StudioTest.tearDown
    login=test_app.StudioTest.login
    post=test_app.StudioTest.post

    def seed(self):
        self.login()
        self.post('/clientes/novo',{'nome':'Cliente Teste','telefone':'41912345678'})
        data=dict(cliente_id='1',servico_id='1',inicio='2026-11-01T10:00',status='Agendado')
        self.post('/agenda/novo',data.copy())
        return data

    def test_old_tab_cannot_overwrite_completed_appointment(self):
        data=self.seed()
        html=self.client.get('/agenda/1/editar').get_data(as_text=True)
        revision=re.search(r'name="revisao" value="(\d+)"',html).group(1)
        completed=dict(data,status='Concluído',revisao=revision)
        self.assertEqual(self.post('/agenda/1/editar',completed).status_code,200)
        response=self.post('/agenda/1/editar',dict(data,revisao=revision))
        self.assertEqual(response.status_code,422)
        self.assertIn('outra aba',response.get_data(as_text=True))
        with sqlite3.connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT status,revisao FROM agendamentos').fetchone(),('Concluído',2))

    def test_invalid_calendar_boundaries_do_not_crash(self):
        self.login()
        with patch('app.agenda.now',return_value=datetime(2026,10,18)):
            for date in ['0001-01-01','9999-12-31','invalida','2000-01-01','2100-12-31']:
                for view in ['dia','semana','mes','ano']:
                    self.assertEqual(self.client.get(f'/agenda?data={date}&visao={view}').status_code,200)

    def test_historical_price_visible_in_edit_form(self):
        self.seed()
        with sqlite3.connect(self.path) as conn:
            conn.execute('UPDATE servicos SET preco=25000 WHERE id=1')
        html=self.client.get('/agenda/1/editar').get_data(as_text=True)
        self.assertIn('Valor combinado: R$ 100,00',html)

    def test_restore_refuses_running_server_without_changing_data(self):
        with patch.object(backup,'DB',self.path),patch('backup.socket.socket') as socket:
            socket.return_value.__enter__.return_value.connect_ex.return_value=0
            with self.assertRaisesRegex(ValueError,'Encerre'):
                backup.restore(self.path.parent/'saved.sqlite3')
        with sqlite3.connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM servicos').fetchone()[0],4)

    def test_restore_preserves_backup_and_invalidates_sessions(self):
        saved=self.path.parent/'saved.sqlite3'
        with patch.object(backup,'DB',self.path),patch.object(backup,'ROOT',self.path.parent),patch('backup.socket.socket') as socket:
            socket.return_value.__enter__.return_value.connect_ex.return_value=111
            backup.backup(saved)
            with sqlite3.connect(self.path) as conn: conn.execute('DELETE FROM servicos')
            backup.restore(saved)
            with sqlite3.connect(self.path) as conn:
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM servicos').fetchone()[0],4)
                self.assertNotEqual(conn.execute('SELECT versao_sessao FROM usuarios').fetchone()[0],1)
            with sqlite3.connect(saved) as conn:
                self.assertEqual(conn.execute('SELECT versao_sessao FROM usuarios').fetchone()[0],1)
            prior=list((self.path.parent/'backups').glob('antes-restauracao-*.sqlite3'))
            self.assertEqual(len(prior),1)
            with sqlite3.connect(prior[0]) as conn:
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM servicos').fetchone()[0],0)
