import calendar, re, sqlite3, string, uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlencode
from flask import Blueprint, request, render_template, redirect, url_for, flash, abort, session
from . import db
bp=Blueprint('agenda',__name__)
STATUSES=('Agendado','Confirmado','Concluído','Cancelado','Não compareceu')
ADDRESS=('cep','logradouro','numero','complemento','bairro','cidade','uf')
def now(): return datetime.now(ZoneInfo('America/Sao_Paulo')).replace(tzinfo=None,microsecond=0)
def migrate(conn):
    cols={x[1] for x in conn.execute('PRAGMA table_info(clientes)')}
    for field in ADDRESS:
        if field not in cols: conn.execute(f"ALTER TABLE clientes ADD COLUMN {field} TEXT NOT NULL DEFAULT ''")
    if 'aceita_mensagens' not in cols: conn.execute('ALTER TABLE clientes ADD COLUMN aceita_mensagens INTEGER NOT NULL DEFAULT 0')
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS agendamentos(id INTEGER PRIMARY KEY, cliente_id INTEGER NOT NULL REFERENCES clientes(id), servico_id INTEGER NOT NULL REFERENCES servicos(id), servico_nome TEXT NOT NULL, inicio TEXT NOT NULL, fim TEXT NOT NULL, duracao INTEGER NOT NULL, preco INTEGER NOT NULL, intervalo INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'Agendado', observacoes TEXT NOT NULL DEFAULT '', revisao INTEGER NOT NULL DEFAULT 1);
    CREATE INDEX IF NOT EXISTS agenda_datas ON agendamentos(inicio,fim);
    CREATE TABLE IF NOT EXISTS modelos(id INTEGER PRIMARY KEY, nome TEXT NOT NULL, tipo TEXT NOT NULL UNIQUE, texto TEXT NOT NULL, ativo INTEGER NOT NULL DEFAULT 1, antecedencia INTEGER NOT NULL DEFAULT 24);
    CREATE TABLE IF NOT EXISTS mensagens(id INTEGER PRIMARY KEY, agendamento_id INTEGER NOT NULL REFERENCES agendamentos(id), modelo_id INTEGER NOT NULL REFERENCES modelos(id), revisao INTEGER NOT NULL, cliente_id INTEGER NOT NULL REFERENCES clientes(id), telefone TEXT NOT NULL, texto TEXT NOT NULL, prevista TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'Pendente', criado_em TEXT NOT NULL, UNIQUE(agendamento_id,modelo_id,revisao));
    ''')
    conn.execute("CREATE TABLE IF NOT EXISTS envios_manuais(id INTEGER PRIMARY KEY, agendamento_id INTEGER NOT NULL REFERENCES agendamentos(id), modelo_id INTEGER NOT NULL REFERENCES modelos(id), telefone TEXT NOT NULL, texto TEXT NOT NULL, criado_em TEXT NOT NULL)")
    for name,kind,text,hours in [('Lembrete do horário','lembrete','Oi, {nome}! Seu horário na Cami Nails é em {data} às {hora}, para {servico}. Te esperamos!',24),('Manutenção','manutencao','Oi, {nome}! Está chegando a hora da sua manutenção em {manutencao}. Vamos reservar seu próximo horário?',48)]:
        conn.execute('INSERT OR IGNORE INTO modelos(nome,tipo,texto,antecedencia) VALUES(?,?,?,?)',(name,kind,text,hours))
    conn.commit()
    from .financeiro import migrate_finance
    migrate_finance(conn)
def audit(action,rid): db().execute('INSERT INTO registros(usuario_id,acao,modulo,registro_id) VALUES(?,?,?,?)',(session['uid'],action,'agenda',rid))
def rows(where='',args=()):
    return db().execute('SELECT a.*,c.nome,c.telefone FROM agendamentos a JOIN clientes c ON c.id=a.cliente_id '+where+' ORDER BY a.inicio',args).fetchall()
@bp.before_request
def protect():
    if not session.get('uid'): return redirect(url_for('login'))
@bp.get('/agenda')
def index():
    try: day=datetime.strptime(request.args.get('data',now().date().isoformat()),'%Y-%m-%d').date()
    except ValueError: day=now().date()
    mode=request.args.get('visao','semana')
    if mode=='ano':
        start=day.replace(month=1,day=1);end=start.replace(year=start.year+1);prev=day.replace(year=day.year-1,day=1);nxt=day.replace(year=day.year+1,day=1)
    elif mode=='mes':
        weeks=calendar.Calendar().monthdatescalendar(day.year,day.month);start=weeks[0][0];end=weeks[-1][-1]+timedelta(days=1)
        prev=(day.replace(day=1)-timedelta(days=1));nxt=(day.replace(day=28)+timedelta(days=4)).replace(day=1)
    elif mode=='dia': start=day;end=day+timedelta(days=1);prev=day-timedelta(days=1);nxt=end
    else: mode='semana';start=day-timedelta(days=day.weekday());end=start+timedelta(days=7);prev=day-timedelta(days=7);nxt=day+timedelta(days=7)
    events=rows('WHERE a.inicio>=? AND a.inicio<?',(start.isoformat(),end.isoformat()))
    days=[start+timedelta(days=i) for i in range((end-start).days)] if mode!='ano' else []
    from .financeiro import stats
    report_start=day.replace(day=1) if mode=='mes' else start
    report_end=(report_start+timedelta(days=32)).replace(day=1) if mode=='mes' else end
    summary=stats(report_start,report_end,mode)
    return render_template('agenda.html',title='Agenda',s=summary,events=events,days=days,day=day,mode=mode,prev=prev,nxt=nxt,today=now().date(),hours=range(24),month_title=['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'][day.month-1]+' '+str(day.year))
@bp.route('/agenda/novo',methods=['GET','POST'])
@bp.route('/agenda/<int:rid>/editar',methods=['GET','POST'])
def edit(rid=None):
    old=db().execute('SELECT * FROM agendamentos WHERE id=?',(rid,)).fetchone() if rid else None
    if rid and not old: abort(404)
    v=dict(old) if old else {'cliente_id':request.args.get('cliente',''),'inicio':request.args.get('data',now().date().isoformat())+'T'+(request.args.get('hora','09:00') if re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]',request.args.get('hora','09:00')) else '09:00'),'status':'Agendado'};error=None
    if request.method=='POST':
        v=request.form.to_dict()
        try:
            cid=int(v.get('cliente_id',''));sid=int(v.get('servico_id',''));start=datetime.fromisoformat(v.get('inicio',''))
            if start.tzinfo or start.year<2000 or start.year>2100: raise ValueError('Informe uma data entre 2000 e 2100, no horário do Studio.')
            status=v.get('status','Agendado');note=v.get('observacoes','').strip()
            if status not in STATUSES or len(note)>2000: raise ValueError('Confira a situação e as observações (até 2.000 caracteres).')
            conn=db();conn.execute('BEGIN IMMEDIATE')
            client=conn.execute('SELECT * FROM clientes WHERE id=?',(cid,)).fetchone();service=conn.execute('SELECT * FROM servicos WHERE id=?',(sid,)).fetchone()
            if not client or (not client['ativo'] and (not old or old['cliente_id']!=cid)): raise ValueError('Selecione uma cliente ativa.')
            if not service or (not service['ativo'] and (not old or old['servico_id']!=sid)): raise ValueError('Selecione um serviço ativo.')
            snapshot=old if old and old['servico_id']==sid else service
            duration=snapshot['duracao'];price=snapshot['preco'];interval=snapshot['intervalo'];name=old['servico_nome'] if old and old['servico_id']==sid else service['nome']
            end=start+timedelta(minutes=duration)
            if end.date()!=start.date(): raise ValueError('O atendimento deve terminar no mesmo dia.')
            if status not in ('Cancelado','Não compareceu') and conn.execute("SELECT id FROM agendamentos WHERE id!=? AND status NOT IN ('Cancelado','Não compareceu') AND inicio<? AND fim>?",(rid or 0,end.isoformat(timespec='minutes'),start.isoformat(timespec='minutes'))).fetchone(): raise ValueError('Esse horário se sobrepõe a outro atendimento. Escolha outro horário.')
            args=(cid,sid,name,start.isoformat(timespec='minutes'),end.isoformat(timespec='minutes'),duration,price,interval,status,note)
            if old:
                conn.execute('UPDATE agendamentos SET cliente_id=?,servico_id=?,servico_nome=?,inicio=?,fim=?,duracao=?,preco=?,intervalo=?,status=?,observacoes=?,revisao=revisao+1 WHERE id=?',(*args,rid))
                conn.execute("UPDATE mensagens SET estado='Cancelada' WHERE agendamento_id=? AND estado IN ('Pendente','Aberta no WhatsApp')",(rid,))
            else: rid=conn.execute('INSERT INTO agendamentos(cliente_id,servico_id,servico_nome,inicio,fim,duracao,preco,intervalo,status,observacoes) VALUES(?,?,?,?,?,?,?,?,?,?)',args).lastrowid
            audit('Edição de agendamento' if old else 'Novo agendamento',rid);conn.commit()
            flash('Agendamento concluído. Receita atualizada automaticamente.' if status=='Concluído' else 'Agendamento salvo. Indicadores atualizados.');return redirect(url_for('agenda.index',data=start.date().isoformat()))
        except (ValueError,OverflowError) as exc:
            db().rollback();error=str(exc) if str(exc) and not str(exc).startswith(('invalid','Invalid')) else 'Selecione cliente, serviço e data válidos.'
    clients=db().execute('SELECT * FROM clientes WHERE ativo=1 OR id=? ORDER BY nome',(old['cliente_id'] if old else 0,)).fetchall()
    services=db().execute('SELECT * FROM servicos WHERE ativo=1 OR id=? ORDER BY nome',(old['servico_id'] if old else 0,)).fetchall()
    return render_template('agenda_form.html',title='Editar agendamento' if old else 'Novo agendamento',v=v,clients=clients,services=services,statuses=STATUSES,error=error),422 if error else 200

def render_message(template,a):
    start=datetime.fromisoformat(a['inicio']);maintenance=start+timedelta(days=a['intervalo'])
    fields={'nome':a['nome'],'data':start.strftime('%d/%m/%Y'),'hora':start.strftime('%H:%M'),'servico':a['servico_nome'],'manutencao':maintenance.strftime('%d/%m/%Y')}
    for _,field,fmt,conversion in string.Formatter().parse(template):
        if field is not None and (field not in fields or fmt or conversion): raise ValueError('Use somente {nome}, {data}, {hora}, {servico} e {manutencao}.')
    return template.format(**fields)

def prepare_queue(conn,clock=None):
    # Compatibility for old launchers: manual messages no longer have a time queue.
    return None

@bp.route('/mensagens',methods=['GET'])
def messages():
    appointments=rows("WHERE c.ativo=1 AND a.status IN ('Agendado','Confirmado') AND a.inicio>=?",(now().date().isoformat(),))
    models=db().execute('SELECT * FROM modelos ORDER BY ativo DESC,nome').fetchall()
    selected=request.args.get('agendamento','');model_id=request.args.get('modelo','')
    chosen=next((a for a in appointments if str(a['id'])==selected),None)
    model=next((m for m in models if str(m['id'])==model_id and m['ativo']),None)
    preview=render_message(model['texto'],chosen) if chosen and model else None
    history=db().execute('SELECT e.*,c.nome FROM envios_manuais e JOIN agendamentos a ON a.id=e.agendamento_id JOIN clientes c ON c.id=a.cliente_id ORDER BY e.id DESC LIMIT 30').fetchall()
    return render_template('messages.html',title='Mensagens',appointments=appointments,models=models,chosen=chosen,model=model,preview=preview,selected=selected,model_id=model_id,history=history)

@bp.post('/mensagens/modelo/novo')
@bp.post('/mensagens/modelo/<int:rid>')
def model_edit(rid=None):
    text=request.form.get('texto','').strip();name=request.form.get('nome','').strip()
    old=db().execute('SELECT * FROM modelos WHERE id=?',(rid,)).fetchone() if rid else None
    if rid and not old: abort(404)
    try:
        if not 2<=len(name)<=80 or not text or len(text)>2000: raise ValueError('Informe um nome de 2 a 80 caracteres e texto de até 2.000 caracteres.')
        render_message(text,dict(nome='Cliente',inicio='2026-01-01T10:00',intervalo=21,servico_nome='Serviço'))
        with db():
            if rid: db().execute('UPDATE modelos SET nome=?,texto=?,ativo=? WHERE id=?',(name,text,1 if request.form.get('ativo') else 0,rid))
            else: db().execute('INSERT INTO modelos(nome,tipo,texto,ativo) VALUES(?,?,?,1)',(name,'manual_'+uuid.uuid4().hex,text))
        flash('Modelo salvo. Selecione um agendamento para usá-lo.')
    except ValueError as e: flash(str(e))
    return redirect(url_for('agenda.messages'))

@bp.post('/mensagens/abrir')
def manual_open():
    try:
        aid=int(request.form.get('agendamento',''));mid=int(request.form.get('modelo',''));revision=int(request.form.get('revisao',''))
    except ValueError: abort(400)
    result=rows('WHERE a.id=? AND c.ativo=1',(aid,));a=result[0] if result else None
    model=db().execute('SELECT * FROM modelos WHERE id=? AND ativo=1',(mid,)).fetchone()
    if not a or not model or a['status'] not in ('Agendado','Confirmado') or a['inicio'][:10]<now().date().isoformat() or a['revisao']!=revision:
        flash('O agendamento ou modelo mudou. Selecione novamente e revise a mensagem.');return redirect(url_for('agenda.messages'))
    text=request.form.get('texto','').strip()
    if not text or len(text)>2000:
        flash('A mensagem deve ter de 1 a 2.000 caracteres.');return redirect(url_for('agenda.messages',agendamento=aid,modelo=mid))
    if request.form.get('telefone')!=a['telefone']:
        flash('O telefone da cliente mudou. Revise o destinatário novamente.');return redirect(url_for('agenda.messages',agendamento=aid,modelo=mid))
    with db():
        db().execute('INSERT INTO envios_manuais(agendamento_id,modelo_id,telefone,texto,criado_em) VALUES(?,?,?,?,?)',(aid,mid,a['telefone'],text,now().isoformat()))
    whatsapp_url='https://wa.me/55'+a['telefone']+'?'+urlencode({'text':text})
    return render_template('whatsapp.html',title='Abrir WhatsApp',whatsapp_url=whatsapp_url,telefone=a['telefone'],texto=text)

@bp.post('/mensagens/<int:rid>/<action>')
def message_action(rid,action):
    flash('O envio agora é manual. Selecione o agendamento e o modelo de mensagem.')
    return redirect(url_for('agenda.messages'))
