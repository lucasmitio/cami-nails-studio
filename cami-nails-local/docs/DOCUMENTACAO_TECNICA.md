# Documentação técnica — Cami Nails

## Objetivo e escopo
Aplicação local para uma profissional do Studio, com cadastro de clientes, agenda, receitas por conclusão e preparação manual de mensagens. Apenas a administradora tem acesso. Os dados ficam no SQLite do computador.

## Arquitetura
Flask organiza as rotas, validações e renderização Jinja. SQLite mantém os dados. Waitress atende em 127.0.0.1:5000. JavaScript local posiciona eventos e desenha gráficos por CSS. O inicializador Windows executa o servidor como processo filho e abre o navegador após verificar sua identificação.

| Módulo | Responsabilidade |
|---|---|
| `app/__init__.py` | Configuração, autenticação, clientes e serviços |
| `app/admin.py` | Alteração de e-mail/senha e versão de sessão |
| `app/agenda.py` | Agendamento, conflitos, modelos e abertura de mensagens |
| `app/financeiro.py` | Indicadores e receitas derivados de agendamentos concluídos |
| `backup.py` | Backup consistente e restauração |
| `limpar_dados.py` | Limpeza operacional autenticada, offline, com backup |

## Modelo de dados
- `usuarios`: e-mail, hash de senha e versão de sessão.
- `clientes`: identificação, telefone, endereço, observações e situação.
- `servicos`: preço em centavos, duração e intervalo sugerido.
- `agendamentos`: cliente/serviço, início/fim, preço e duração históricos, situação e revisão.
- `modelos`: modelos editáveis com variáveis.
- `envios_manuais`: texto e destinatário usados na abertura do WhatsApp.
- `registros`: trilha de ações administrativas.
- `login_tentativas`: limitação de tentativas de autenticação.
- `mensagens` e `financeiro`: tabelas legadas preservadas para compatibilidade; não determinam a receita atual.

## Regras
Cada conclusão contribui uma vez para receita, pelo valor armazenado no próprio agendamento. Não existe duplicação por salvar repetidamente. A data do serviço determina o período. Reabrir/cancelar retira essa contribuição. Agendado e Confirmado compõem receita prevista. Alterar preço do catálogo preserva os valores anteriores.
Conflitos são validados dentro de uma transação com bloqueio de escrita, considerando o intervalo completo. Cancelamento/falta liberam o horário. A agenda considera o fuso de São Paulo.

## Acesso e privacidade
Senhas com hash Werkzeug, CSRF nos formulários, sessão HTTP-only/SameSite, validação no servidor e limite de tentativas no login. Mudança de credenciais incrementa a versão de sessão e invalida sessões anteriores. Banco e backups são arquivos locais sem criptografia de disco; proteja a conta Windows e o dispositivo. Não há recuperação por e-mail, múltiplos perfis de permissão ou configuração pronta para internet.

## Dados de teste e entrada em operação
A limpeza preserva administradora, catálogo e modelos. Clientes, agendamentos e históricos são removidos somente após autenticação, confirmação literal e backup verificado. O banco do computador do Studio não pode ser apagado pelo arquivo ZIP: é necessário executar o procedimento local.

## Publicação e evolução
O repositório não inclui dados privados. Não há licença de redistribuição definida pelo proprietário. GitHub é usado para código e documentação; não hospeda o servidor Flask via Pages. Ampliações futuras podem incluir recuperação de acesso, distribuição instalável e hospedagem apropriada.
