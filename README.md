# Cami Nails — Gestão do Studio

Sistema web local para uso administrativo do Studio Cami Nails, desenvolvido como projeto extensionista. Organiza clientes, serviços, agendamentos, mensagens e receitas dos atendimentos concluídos.

## Funcionalidades
- Login administrativo e alteração de e-mail/senha com validação da senha atual.
- Cadastro de clientes com endereço, WhatsApp formatado, preferências e inativação.
- Serviços com preço, duração e intervalo sugerido de manutenção.
- Agenda diária, semanal, mensal e anual; bloqueio de conflitos de horário.
- Modelos de mensagens com seleção de agendamento, revisão e abertura no WhatsApp.
- Dashboard e receitas com filtros de semana, mês e ano.
- Receita calculada uma única vez pelo valor do agendamento concluído; sem despesas ou lançamento manual.
- Atalho Windows, backup, restauração e limpeza autenticada dos dados de teste.

## Começar no Windows
Requisitos: Python 3.11 ou superior, navegador e internet para instalar as dependências. Extraia o projeto para uma pasta permanente e execute `instalar_atalho.bat`. Na instalação nova, informe o e-mail e uma senha de pelo menos 12 caracteres. Em instalações existentes, a conta é preservada. Depois use o ícone **Cami Nails** na Área de Trabalho.

Leia [TUTORIAL_DE_USO.txt](TUTORIAL_DE_USO.txt) antes de começar. Não mova a pasta depois de criar o atalho. Para atualizar, feche o sistema, faça backup, substitua os arquivos do programa preservando `instance` e `.venv`, e execute `atualizar.bat`.

## Instalação por terminal
Abra o terminal na pasta que contém `run.py`:
```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m flask --app run init-db
.venv\Scripts\python -m flask --app run criar-admin
.venv\Scripts\python run.py
```
Acesse http://127.0.0.1:5000. No Linux/macOS use `python3 -m venv .venv` e `.venv/bin/python`; o atalho é específico do Windows.

## Tecnologias e estrutura
Flask, Jinja, SQLite, Waitress, HTML, CSS e JavaScript. Gráficos locais, sem dependência de serviços externos.

| Pasta / arquivo | Finalidade |
|---|---|
| `app/` | Aplicação, rotas, templates e recursos visuais |
| `tests/` | Testes automatizados com bancos temporários |
| `docs/` | Documentação técnica, validação e guia de publicação |
| `run.py` | Servidor local |
| `abrir_studio.pyw` | Inicializador com janela de controle |
| `instalar_atalho.bat` | Instalação e criação do atalho |
| `backup.py` / `fazer_backup.bat` | Backup do banco |
| `limpar_dados.py` / `zerar_dados_teste.bat` | Limpeza autenticada com backup |
| `instance/` | Dados locais, criados na instalação e ignorados pelo Git |

## Testes
```powershell
.venv\Scripts\python -m unittest discover -s tests -v
```
A validação funcional automatizada não substitui a conferência do atalho no Windows do Studio nem a avaliação com Camila. Não há dados reais ou credenciais neste repositório.

## Limites
Uso em um computador, com uma profissional e uma conta administradora. A receita representa serviços concluídos, não confirmação bancária. O envio do WhatsApp é manual após revisão; não há integração de disparo automático. Não há sincronização com Google Agenda, estoque, despesas ou acesso das clientes. O servidor não está configurado para exposição à internet. GitHub armazena o código; GitHub Pages não executa este servidor Flask.

## Documentação
- [Tutorial de uso](TUTORIAL_DE_USO.txt)
- [Documentação técnica](docs/DOCUMENTACAO_TECNICA.md)
- [Roteiro de validação](docs/VALIDACAO.md)
- [Como publicar no GitHub](docs/GITHUB_PASSO_A_PASSO.txt)

Registros e resultados de uso real devem ser acrescentados somente após a aplicação no Studio. Não publique o banco, backups, credenciais ou imagens com dados pessoais de clientes.
