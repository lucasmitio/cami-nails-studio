"""Limpeza operacional autenticada, com servidor parado e backup obrigatório."""
from pathlib import Path
import sqlite3,socket,getpass
from datetime import datetime
from werkzeug.security import check_password_hash
ROOT=Path(__file__).resolve().parent
TABLES=('envios_manuais','mensagens','financeiro','agendamentos','clientes','registros','login_tentativas')
def reset_data(database,backup_dir,email,password):
 with sqlite3.connect(database,timeout=5) as conn:
  user=conn.execute('SELECT id,senha FROM usuarios WHERE email=?',(email.strip().lower(),)).fetchone()
  if not user or not check_password_hash(user[1],password):raise ValueError('E-mail ou senha incorretos. Nenhum dado foi apagado.')
  backup_dir=Path(backup_dir);backup_dir.mkdir(parents=True,exist_ok=True)
  path=backup_dir/('antes-limpeza-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sqlite3')
  with sqlite3.connect(path) as dest:
   conn.backup(dest)
   if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Backup inválido. Limpeza interrompida.')
  with conn:
   conn.execute('PRAGMA foreign_keys=ON')
   for table in TABLES:conn.execute('DELETE FROM '+table)
   conn.execute('UPDATE usuarios SET versao_sessao=versao_sessao+1')
 return path
if __name__=='__main__':
 try:
  with socket.socket() as sock:
   sock.settimeout(1)
   if sock.connect_ex(('127.0.0.1',5000))==0:raise ValueError('Encerre o sistema antes de limpar os dados.')
  db=ROOT/'instance'/'studio.sqlite3'
  if not db.is_file():raise ValueError('Banco não encontrado. Faça a instalação primeiro.')
  print('Apaga clientes, agendamentos, receitas e históricos. Preserva conta, serviços e modelos.')
  email=input('E-mail da administradora: ');password=getpass.getpass('Senha atual: ')
  if input('Digite ZERAR para confirmar: ').strip()!='ZERAR':raise ValueError('Operação cancelada. Nenhum dado apagado.')
  path=reset_data(db,ROOT/'backups',email,password)
  print('Dados de teste removidos. Backup:',path)
 except (ValueError,sqlite3.Error,OSError) as error:
  print('Não foi possível concluir:',error);raise SystemExit(1)
