import os, re, secrets, sqlite3, hmac
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps
import click
from flask import Flask, g, session, request, redirect, url_for, render_template, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

SCHEMA = '''
CREATE TABLE IF NOT EXISTS usuarios(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, senha TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS clientes(id INTEGER PRIMARY KEY, nome TEXT NOT NULL, telefone TEXT UNIQUE NOT NULL, nascimento TEXT NOT NULL DEFAULT '', instagram TEXT NOT NULL DEFAULT '', observacoes TEXT NOT NULL DEFAULT '', ativo INTEGER NOT NULL DEFAULT 1 CHECK(ativo IN (0,1)));
CREATE TABLE IF NOT EXISTS servicos(id INTEGER PRIMARY KEY, nome TEXT NOT NULL, preco INTEGER NOT NULL CHECK(preco>=0), duracao INTEGER NOT NULL CHECK(duracao>0), intervalo INTEGER NOT NULL CHECK(intervalo>=0), descricao TEXT NOT NULL DEFAULT '', ativo INTEGER NOT NULL DEFAULT 1 CHECK(ativo IN (0,1)));
CREATE TABLE IF NOT EXISTS registros(id INTEGER PRIMARY KEY, usuario_id INTEGER NOT NULL REFERENCES usuarios(id), acao TEXT NOT NULL, modulo TEXT NOT NULL, registro_id INTEGER, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS login_tentativas(id INTEGER PRIMARY KEY, endereco TEXT NOT NULL, instante INTEGER NOT NULL);
'''

def db():
    if 'db' not in g:
        g.db=sqlite3.connect(g.app_database, timeout=15)
        g.db.row_factory=sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db

def create_app(config=None):
    app=Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True,exist_ok=True)
    secret=Path(app.instance_path)/'session.key'
    if not secret.exists():
        try:
            with secret.open('x') as f: f.write(secrets.token_hex(32))
            secret.chmod(0o600)
        except FileExistsError: pass
    app.config.update(SECRET_KEY=secret.read_text(), DATABASE=str(Path(app.instance_path)/'studio.sqlite3'), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', PERMANENT_SESSION_LIFETIME=timedelta(hours=8), MAX_CONTENT_LENGTH=64*1024)
    if config: app.config.update(config)
    from .agenda import bp, migrate, ADDRESS, rows, now
    app.register_blueprint(bp)
    from .financeiro import bp as finance_bp
    app.register_blueprint(finance_bp)
    from .admin import bp as admin_bp, migrate_admin
    app.register_blueprint(admin_bp)
    if Path(app.config['DATABASE']).exists():
        with sqlite3.connect(app.config['DATABASE']) as conn:
            if conn.execute("SELECT 1 FROM sqlite_master WHERE name='clientes'").fetchone():
                columns={r[1] for r in conn.execute('PRAGMA table_info(clientes)')}
                if 'cep' not in columns:
                    dest=Path(app.config['DATABASE']).with_suffix('.antes-etapa2.sqlite3')
                    if not dest.exists():
                        with sqlite3.connect(dest) as backup_conn: conn.backup(backup_conn)
                migrate(conn)
                migrate_admin(conn)
    @app.template_filter('phone')
    def phone_display(value):
        value=re.sub(r'\D','',value or '')
        return f'({value[:2]}) {value[2:-4]}-{value[-4:]}' if len(value) in (10,11) else value
    @app.template_filter('brdate')
    def brdate(value):
        from datetime import datetime
        return datetime.fromisoformat(value).strftime('%d/%m/%Y às %H:%M')
    @app.before_request
    def prepare():
        g.app_database=app.config['DATABASE']
        if session.get('uid'):
            account=db().execute('SELECT versao_sessao FROM usuarios WHERE id=?',(session['uid'],)).fetchone()
            if not account or session.get('auth_version')!=account['versao_sessao']:
                session.clear()
                if request.endpoint not in ('login','static','health'): return redirect(url_for('login'))
        if 'csrf' not in session: session['csrf']=secrets.token_hex(32)
        if request.method=='POST' and not hmac.compare_digest(session['csrf'], request.form.get('csrf','')): abort(400, 'Formulário expirado. Recarregue a página.')
    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Content-Security-Policy']="default-src 'self'; style-src 'self'; form-action 'self'; frame-ancestors 'none'"
        response.headers['Cache-Control']='no-store'
        return response
    @app.teardown_appcontext
    def close(_):
        if conn:=g.pop('db',None): conn.close()
    def protected(fn):
        @wraps(fn)
        def wrapped(*a,**k):
            if not session.get('uid'): return redirect(url_for('login'))
            return fn(*a,**k)
        return wrapped
    def log(action,module,rid):
        db().execute('INSERT INTO registros(usuario_id,acao,modulo,registro_id) VALUES(?,?,?,?)',(session['uid'],action,module,rid))
    @app.template_filter('money')
    def money(cents): return f'R$ {cents/100:,.2f}'.replace(',','X').replace('.',',').replace('X','.')
    @app.get('/saude')
    def health():
        import hashlib
        root=Path(__file__).resolve().parent.parent
        return {'app':'cami-nails','installation':hashlib.sha256(str(root).encode()).hexdigest()[:16]}
    @app.route('/login',methods=['GET','POST'])
    def login():
        import time
        if request.method=='POST':
            now=int(time.time()); ip=request.remote_addr or 'local'
            db().execute('DELETE FROM login_tentativas WHERE instante < ?',(now-900,)); db().commit()
            count=db().execute('SELECT COUNT(*) FROM login_tentativas WHERE endereco=?',(ip,)).fetchone()[0]
            if count>=5: return render_template('login.html',error='Muitas tentativas. Aguarde 15 minutos.'),429
            user=db().execute('SELECT * FROM usuarios WHERE email=?',(request.form.get('email','').strip().lower(),)).fetchone()
            if user and check_password_hash(user['senha'],request.form.get('senha','')):
                db().execute('DELETE FROM login_tentativas WHERE endereco=?',(ip,)); db().commit()
                session.clear(); session.update(uid=user['id'],auth_version=user['versao_sessao'],csrf=secrets.token_hex(32)); session.permanent=True
                return redirect(url_for('dashboard'))
            db().execute('INSERT INTO login_tentativas(endereco,instante) VALUES(?,?)',(ip,now));db().commit()
            return render_template('login.html',error='E-mail ou senha incorretos.'),401
        return render_template('login.html')
    @app.post('/sair')
    def logout():
        session.clear(); return redirect(url_for('login'))
    @app.get('/')
    @protected
    def dashboard():
        from .financeiro import dashboard as render_dashboard
        return render_dashboard()
    @app.get('/clientes')
    @protected
    def clients():
        q=request.args.get('q','').strip()[:100]
        status=request.args.get('status','ativos')
        rows=db().execute('SELECT * FROM clientes WHERE (nome LIKE ? OR telefone LIKE ?) AND (? = ? OR ativo=?) ORDER BY nome COLLATE NOCASE',('%'+q+'%','%'+(re.sub(r'\D','',q) if re.search(r'\d',q) else q)+'%',status,'todos',0 if status=='inativos' else 1)).fetchall()
        return render_template('clients.html',title='Clientes',rows=rows,q=q,status=status)
    @app.route('/clientes/novo',methods=['GET','POST'])
    @app.route('/clientes/<int:rid>/editar',methods=['GET','POST'])
    @protected
    def client_edit(rid=None):
        row=db().execute('SELECT * FROM clientes WHERE id=?',(rid,)).fetchone() if rid else None
        if rid and not row: abort(404)
        values=dict(row) if row else {}; error=None
        if request.method=='POST':
            values={k:request.form.get(k,'').strip() for k in ['nome','telefone','nascimento','instagram','observacoes',*ADDRESS]}
            try:
                phone=re.sub(r'\D','',values['telefone'])
                if len(phone) in (12,13) and phone.startswith('55'): phone=phone[2:]
                if not 2<=len(values['nome'])<=100: raise ValueError('Informe um nome entre 2 e 100 caracteres.')
                if len(phone) not in (10,11): raise ValueError('Informe o telefone com DDD (10 ou 11 dígitos).')
                values['telefone']=phone
                if len(values['instagram'])>100 or len(values['observacoes'])>2000: raise ValueError('Instagram: até 100 caracteres. Observações: até 2.000.')
                if values['nascimento'] and date.fromisoformat(values['nascimento'])>date.today(): raise ValueError('Nascimento não pode estar no futuro.')
                values['aceita_mensagens']=1 if request.form.get('aceita_mensagens') else 0
                values['cep']=re.sub(r'\D','',values['cep'])
                values['uf']=values['uf'].upper()
                if values['cep'] and len(values['cep'])!=8: raise ValueError('O CEP deve ter 8 dígitos.')
                if values['uf'] and values['uf'] not in 'AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split(): raise ValueError('Informe uma UF válida, como PR.')
                if any(len(values[k])>150 for k in ADDRESS): raise ValueError('Use até 150 caracteres por campo do endereço.')
                with db():
                    if rid: db().execute('UPDATE clientes SET nome=?,telefone=?,nascimento=?,instagram=?,observacoes=?,cep=?,logradouro=?,numero=?,complemento=?,bairro=?,cidade=?,uf=?,aceita_mensagens=? WHERE id=?',(*values.values(),rid))
                    else: rid=db().execute('INSERT INTO clientes(nome,telefone,nascimento,instagram,observacoes,cep,logradouro,numero,complemento,bairro,cidade,uf,aceita_mensagens) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',tuple(values.values())).lastrowid
                    log('Cadastro' if not row else 'Edição','clientes',rid)
                flash('Cliente salva com sucesso.'); return redirect(url_for('client_detail',rid=rid))
            except sqlite3.IntegrityError: error='Este telefone já está cadastrado. Busque a cliente, inclusive entre as inativas.'
            except ValueError as e: error=str(e)
        return render_template('client_form.html',title='Editar cliente' if row else 'Nova cliente',v=values,error=error),422 if error else 200
    @app.get('/clientes/<int:rid>')
    @protected
    def client_detail(rid):
        row=db().execute('SELECT * FROM clientes WHERE id=?',(rid,)).fetchone()
        if not row: abort(404)
        return render_template('client_detail.html',title='Ficha da cliente',c=row,events=rows('WHERE a.cliente_id=?',(rid,)))
    @app.get('/servicos')
    @protected
    def services():
        return render_template('services.html',title='Serviços',rows=db().execute('SELECT * FROM servicos ORDER BY ativo DESC,nome').fetchall())
    @app.route('/servicos/novo',methods=['GET','POST'])
    @app.route('/servicos/<int:rid>/editar',methods=['GET','POST'])
    @protected
    def service_edit(rid=None):
        row=db().execute('SELECT * FROM servicos WHERE id=?',(rid,)).fetchone() if rid else None
        if rid and not row: abort(404)
        v=dict(row) if row else {}; error=None
        if row: v['preco']=str(Decimal(row['preco'])/100)
        if request.method=='POST':
            v={k:request.form.get(k,'').strip() for k in ['nome','preco','duracao','intervalo','descricao']}
            try:
                price=Decimal(v['preco'].replace(',','.'))
                if not price.is_finite() or price<0 or price>100000 or price*100 != (price*100).to_integral_value(): raise ValueError()
                duration=int(v['duracao']); interval=int(v['intervalo'])
                if not 2<=len(v['nome'])<=100 or not 1<=duration<=720 or not 0<=interval<=365 or len(v['descricao'])>1000: raise ValueError()
                args=(v['nome'],int(price*100),duration,interval,v['descricao'])
                with db():
                    if rid: db().execute('UPDATE servicos SET nome=?,preco=?,duracao=?,intervalo=?,descricao=? WHERE id=?',(*args,rid))
                    else: rid=db().execute('INSERT INTO servicos(nome,preco,duracao,intervalo,descricao) VALUES(?,?,?,?,?)',args).lastrowid
                    log('Edição' if row else 'Cadastro','servicos',rid)
                flash('Serviço salvo.'); return redirect(url_for('services'))
            except (ValueError,InvalidOperation): error='Confira nome, preço (até 2 casas decimais), duração (1–720 minutos) e manutenção (0–365 dias).'
        return render_template('service_form.html',title='Editar serviço' if row else 'Novo serviço',v=v,error=error),422 if error else 200
    @app.post('/<kind>/<int:rid>/status')
    @protected
    def toggle(kind,rid):
        if kind not in ('clientes','servicos'): abort(404)
        with db():
            cursor=db().execute(f'UPDATE {kind} SET ativo=1-ativo WHERE id=?',(rid,))
            if not cursor.rowcount: abort(404)
            log('Alteração de situação',kind,rid)
        flash('Situação atualizada; dados preservados.')
        return redirect(url_for('clients' if kind=='clientes' else 'services'))
    @app.cli.command('init-db')
    def init_db():
        conn=sqlite3.connect(app.config['DATABASE']);conn.executescript(SCHEMA)
        if not conn.execute('SELECT 1 FROM servicos').fetchone():
            conn.executemany('INSERT INTO servicos(nome,preco,duracao,intervalo,descricao) VALUES(?,?,?,?,?)',[(n,p,d,21,'Duração e manutenção sugeridas: revise conforme a rotina do Studio.') for n,p,d in [('Alongamento Molde F1',10000,120),('Manutenção',8000,90),('Banho de Gel',7000,90),('Blindagem',6000,60)]])
        conn.commit();migrate(conn);migrate_admin(conn);conn.close();click.echo('Banco preparado e atualizado.')
    @app.cli.command('criar-admin')
    @click.option('--email',prompt=True)
    @click.password_option(confirmation_prompt=True)
    def admin(email,password):
        if len(password)<12 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email.strip()): raise click.ClickException('Use e-mail válido e senha com pelo menos 12 caracteres.')
        with sqlite3.connect(app.config['DATABASE']) as conn:
            if conn.execute('SELECT 1 FROM usuarios').fetchone(): raise click.ClickException('Administradora já configurada.')
            conn.execute('INSERT INTO usuarios(email,senha) VALUES(?,?)',(email.strip().lower(),generate_password_hash(password)))
        click.echo('Administradora criada.')
    return app
