import argparse, sqlite3
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
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--restaurar',type=Path);parser.add_argument('--confirmar-servidor-fechado',action='store_true');args=parser.parse_args()
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    if args.restaurar:
        if not args.confirmar_servidor_fechado: parser.error('Feche o sistema e acrescente --confirmar-servidor-fechado.')
        validate(args.restaurar)
        if DB.exists(): backup(ROOT/'backups'/f'antes-restauracao-{stamp}.sqlite3')
        DB.parent.mkdir(exist_ok=True)
        with sqlite3.connect(args.restaurar) as source, sqlite3.connect(DB) as target: source.backup(target)
        print('Backup restaurado. A senha será a existente na data do backup.')
    else:
        dest=ROOT/'backups'/f'studio-{stamp}.sqlite3';backup(dest);print(f'Backup criado: {dest}')
