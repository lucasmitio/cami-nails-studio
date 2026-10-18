import re,secrets,sqlite3
from flask import Blueprint,request,session,redirect,url_for,render_template,flash
from werkzeug.security import check_password_hash,generate_password_hash
from . import db
bp=Blueprint('admin',__name__)
def migrate_admin(conn):
 if 'versao_sessao' not in {r[1] for r in conn.execute('PRAGMA table_info(usuarios)')}:
  conn.execute('ALTER TABLE usuarios ADD COLUMN versao_sessao INTEGER NOT NULL DEFAULT 1')
 conn.commit()
@bp.route('/administracao',methods=['GET','POST'])
def account():
 if not session.get('uid'):return redirect(url_for('login'))
 user=db().execute('SELECT * FROM usuarios WHERE id=?',(session['uid'],)).fetchone()
 error=None
 if request.method=='POST':
  email=request.form.get('email','').strip().lower();password=request.form.get('nova_senha','');confirmation=request.form.get('confirmacao','')
  if not check_password_hash(user['senha'],request.form.get('senha_atual','')):error='A senha atual está incorreta.'
  elif not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(email)>254:error='Informe um e-mail válido.'
  elif password and (len(password)<12 or len(password)>128):error='A nova senha deve ter entre 12 e 128 caracteres.'
  elif password!=confirmation:error='A confirmação da nova senha não confere.'
  else:
   try:
    with db():
     db().execute('UPDATE usuarios SET email=?,senha=?,versao_sessao=versao_sessao+1 WHERE id=?',(email,generate_password_hash(password) if password else user['senha'],user['id']))
     db().execute('INSERT INTO registros(usuario_id,acao,modulo,registro_id) VALUES(?,?,?,?)',(user['id'],'Alteração da conta administradora','admin',user['id']))
    session.clear();flash('Conta atualizada. Entre novamente com seus dados.');return redirect(url_for('login'))
   except sqlite3.IntegrityError:error='Este e-mail já está em uso.'
 return render_template('admin.html',title='Administração',user=user,error=error),422 if error else 200
