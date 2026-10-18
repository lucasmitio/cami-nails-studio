import argparse, sqlite3, socket
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parent
DB=ROOT/'instance'/'studio.sqlite3'
def validate(path):
    with sqlite3.connect(f'{path.resolve().as_uri()}?mode=ro',uri=True) as c:
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Banco danificado.')
        names={r[0] for r in c.execute('SELECT name FROM sqlite_master WHERE type="table"')}
        if not {'usuarios','clientes','servicos','registros','login_tentativas'}<=names: raise ValueError('Arquivo incompatível.')
def backup(dest):
    validate(DB);dest.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(DB) as source, sqlite3.connect(dest) as target: source.backup(target)
    validate(dest)
def restore(source_path):
    source_path=Path(source_path)
    if source_path.resolve()==DB.resolve():
        raise ValueError('Selecione um arquivo de backup diferente do banco em uso.')
    with socket.socket() as sock:
        sock.settimeout(1)
        if sock.connect_ex(('127.0.0.1',5000))==0:
            raise ValueError('Encerre o sistema antes de restaurar o backup.')
    validate(source_path)
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    if DB.exists(): backup(ROOT/'backups'/f'antes-restauracao-{stamp}.sqlite3')
    DB.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(f'{source_path.resolve().as_uri()}?mode=ro',uri=True) as source, sqlite3.connect(DB) as target:
        source.backup(target)
        # Restored sessions must not reuse cookies from before restoration.
        cols={r[1] for r in target.execute('PRAGMA table_info(usuarios)')}
        if 'versao_sessao' in cols:
            import secrets
            target.execute('UPDATE usuarios SET versao_sessao=?',(secrets.randbits(62),))
    validate(DB)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--restaurar',type=Path);parser.add_argument('--confirmar-servidor-fechado',action='store_true');args=parser.parse_args()
    try:
        if args.restaurar:
            if not args.confirmar_servidor_fechado: parser.error('Feche o sistema e acrescente --confirmar-servidor-fechado.')
            restore(args.restaurar)
            print('Backup restaurado. Entre novamente com a senha existente na data do backup.')
        else:
            stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            dest=ROOT/'backups'/f'studio-{stamp}.sqlite3';backup(dest);print(f'Backup criado: {dest}')
    except (ValueError,sqlite3.Error,OSError) as error:
        print('Não foi possível concluir:',error)
        raise SystemExit(1)
