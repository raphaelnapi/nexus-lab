# Arquitetura

## Planos separados

1. **Produto:** repositório versionado, sem dados de caso.
2. **Evidência:** cofre externo somente leitura.
3. **Casos:** workspaces externos graváveis, um banco SQLite por caso.
4. **Ferramentas:** raiz externa com binários previamente validados.
5. **Worker:** VM Hyper-V opcional para métodos incompatíveis com Windows.

PowerShell é a interface do operador. O núcleo Python é a única camada autorizada a alterar registros estruturados. Ferramentas produzem arquivos no workspace; o núcleo registra hashes e proveniência.

## Integridade dos registros

O banco usa foreign keys, transações imediatas e `synchronous=FULL`. `custody_events` e `audit_events` possuem triggers que impedem alteração ou exclusão. Cada evento de auditoria incorpora o hash do evento anterior. Checkpoints preservam o último hash coberto e começam como `unsigned` até existir uma política real de certificados e chaves.

O ledger detecta alteração; não transforma SQLite em mídia WORM. Controles de armazenamento, backup, ACL, BitLocker, revisão e assinatura continuam necessários.

## Proveniência

Entradas e saídas são relações de primeira classe. `provenance_edges` complementa as relações específicas para sustentar o encadeamento entre conclusão, achado, afirmação, artefato, execução, cópia e evidência.

