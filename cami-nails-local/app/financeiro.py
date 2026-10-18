import calendar, secrets, sqlite3
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from flask import Blueprint,request,render_template,redirect,url_for,session,flash,abort
from . import db
from .agenda import now, STATUSES
bp=Blueprint('financeiro',__name__)
METHODS=('Pix','Dinheiro','Cartão de débito','Cartão de crédito','Transferência')
def migrate_finance(conn):
 conn.executescript('''CREATE TABLE IF NOT EXISTS financeiro(id INTEGER PRIMARY KEY, tipo TEXT NOT NULL CHECK(tipo IN ('Receita','Despesa')), valor INTEGER NOT NULL CHECK(valor>0), data TEXT NOT NULL, descricao TEXT NOT NULL, categoria TEXT NOT NULL, forma TEXT NOT NULL, agendamento_id INTEGER REFERENCES agendamentos(id), usuario_id INTEGER NOT NULL REFERENCES usuarios(id), chave TEXT NOT NULL UNIQUE, estornado INTEGER NOT NULL DEFAULT 0, motivo_estorno TEXT NOT NULL DEFAULT '', criado_em TEXT NOT NULL, estornado_em TEXT);
 CREATE INDEX IF NOT EXISTS financeiro_data ON financeiro(data);
 CREATE INDEX IF NOT EXISTS financeiro_agendamento ON financeiro(agendamento_id);
 ''');conn.commit()
def period():
 mode=request.args.get('periodo','mes')
 if mode not in ('semana','mes','ano'): mode='mes'
 try: anchor=date.fromisoformat(request.args.get('data',now().date().isoformat()))
 except ValueError: anchor=now().date()
 if not 2000<=anchor.year<=2100: anchor=now().date()
 if mode=='ano': start=date(anchor.year,1,1);end=date(anchor.year+1,1,1)
 elif mode=='mes': start=anchor.replace(day=1);end=(start+timedelta(days=32)).replace(day=1)
 else: start=anchor-timedelta(days=anchor.weekday());end=start+timedelta(days=7)
 return mode,anchor,start,end

def stats(start,end,mode):
 # Revenue has one source of truth: completed appointments and their agreed price.
 appointments=[dict(r) for r in db().execute('SELECT a.*,c.nome FROM agendamentos a JOIN clientes c ON c.id=a.cliente_id WHERE a.inicio>=? AND a.inicio<? ORDER BY a.inicio',(start.isoformat(),end.isoformat()))]
 status={label:0 for label in STATUSES};income=expected=0
 buckets={};cursor=start
 while cursor<end:
  key=cursor.strftime('%Y-%m') if mode=='ano' else cursor.isoformat()
  buckets[key]={'label':cursor.strftime('%m/%Y') if mode=='ano' else cursor.strftime('%d/%m'),'receita':0,'agendamentos':0}
  cursor=(cursor.replace(day=1)+timedelta(days=32)).replace(day=1) if mode=='ano' else cursor+timedelta(days=1)
 for a in appointments:
  status[a['status']]+=1
  a['receita']=a['preco'] if a['status']=='Concluído' else 0
  income+=a['receita']
  if a['status'] in ('Agendado','Confirmado'):expected+=a['preco']
  key=a['inicio'][:7] if mode=='ano' else a['inicio'][:10]
  if key in buckets:
   buckets[key]['agendamentos']+=1;buckets[key]['receita']+=a['receita']
 completed=status['Concluído']
 return dict(appointments=appointments,status=status,income=income,expected=expected,completed=completed,ticket=round(income/completed) if completed else 0,buckets=list(buckets.values()))

def dashboard():
 mode,anchor,start,end=period();data=stats(start,end,mode)
 today=now().date().isoformat()
 daily=db().execute('SELECT a.*,c.nome FROM agendamentos a JOIN clientes c ON c.id=a.cliente_id WHERE substr(a.inicio,1,10)=? ORDER BY a.inicio',(today,)).fetchall()
 return render_template('dashboard.html',title='Visão geral',mode=mode,anchor=anchor,start=start,end=end-timedelta(days=1),s=data,daily=daily,clients=db().execute('SELECT COUNT(*) FROM clientes WHERE ativo=1').fetchone()[0])
@bp.before_request
def auth():
 if not session.get('uid'):return redirect(url_for('login'))
@bp.get('/financeiro')
def index():
 mode,anchor,start,end=period()
 return render_template('financeiro.html',title='Receitas',mode=mode,anchor=anchor,start=start,end=end-timedelta(days=1),s=stats(start,end,mode))
@bp.route('/financeiro/novo',methods=['GET','POST'])
@bp.route('/financeiro/<int:rid>/estornar',methods=['GET','POST'])
def retired(rid=None):
 flash('As receitas agora são calculadas automaticamente pelos agendamentos concluídos. Ajuste o agendamento para corrigir um valor.')
 return redirect(url_for('financeiro.index'))
