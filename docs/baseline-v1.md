# Baseline legado v1

Baseline observado antes da reformulação:

- Sete skills acopladas a WSL, Bash e catálogo `apt`.
- Código reutilizável limitado ao hashing de um arquivo.
- SQLite por caso sem schema version inicial, approvals, ledger, timelines ou múltiplas entradas/saídas.
- Seis testes unitários, todos aprovados antes da migração de código.
- Windows PowerShell 5.1 presente; PowerShell 7.6, Pester 5 e cmdlets Hyper-V ausentes no diagnóstico inicial.
- Caso legado e manifestos presentes em diretórios ignorados pelo Git.

Os arquivos WSL versionados foram substituídos pela arquitetura v2. Dados ignorados sob `Evidence/`, `Lab/cases/` e `Registry/` não foram removidos nem atualizados. Use o preview do migrador antes de criar uma cópia v2 externa.
