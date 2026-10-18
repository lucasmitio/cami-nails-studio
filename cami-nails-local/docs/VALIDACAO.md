# Validação e evidências

## Testes automatizados

Resultado desta versão: 32 testes aprovados no ambiente de desenvolvimento. O atalho Windows e a utilização no Studio permanecem sujeitos à conferência local.
Execute `python -m unittest discover -s tests -v` dentro do ambiente virtual. Os testes usam bases temporárias e não enviam mensagens reais. Cobrem autenticação, cadastro, conflitos, receita por conclusão, filtros, mensagens, backup, gerenciamento de conta e limpeza do banco.

## Conferência no Studio (preencher após executar)
- [ ] Atalho inicia servidor e navegador no Windows.
- [ ] Administradora altera e-mail/senha e entra novamente.
- [ ] Cadastro e endereço persistem após fechar/reabrir.
- [ ] Agenda bloqueia horários sobrepostos.
- [ ] Conclusão atualiza receita sem duplicar.
- [ ] Modelos abrem texto correto para o número de teste.
- [ ] Backup é criado e uma restauração foi verificada em cópia separada.
- [ ] Dados de teste foram limpos antes do cadastro real.
- [ ] Camila recebeu orientação e registrou feedback.

## Campos para registrar evidências reais
Data da aplicação: a preencher.
Participante/responsável: a preencher com autorização.
Feedback: a preencher.
Resultados observados: a preencher; não confundir com funcionalidades previstas.
Vídeo de demonstração: inserir link após publicação.
Vídeo de utilização/validação: inserir link após gravação autorizada.
Repositório: https://github.com/lucasmitio/cami-nails-studio

Use dados fictícios nas gravações. Estes campos auxiliam a documentação; confira as exigências do formulário vigente da disciplina antes da entrega. Não constituem comprovação de atividades ainda não realizadas.

## Revisão de 18/10/2026

Testes adicionais: edição simultânea em duas abas, datas extremas da agenda, exibição do preço histórico, bloqueio de restauração com servidor aberto e restauração com preservação do backup anterior e invalidação das sessões.
