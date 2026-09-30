# Nexus-Lab v2

Nexus-Lab v2 é um laboratório local Windows-first para exames de perícia digital assistidos por agentes. PowerShell 7.6+ oferece a interface operacional; um núcleo Python transacional mantém hashes, SQLite, migrações, proveniência e ledger. Ferramentas sem equivalente Windows validado podem ser executadas em um worker Linux Hyper-V isolado e explicitamente autorizado.

O projeto não inclui evidências ou casos reais. Dados operacionais ficam em raízes externas configuradas:

```text
<evidence-root>/                 cofre somente leitura
<case-root>/<case-id>/           registros, cópias e resultados
<tool-root>/                     binários validados e imutáveis durante exames
```

## Requisitos

- Windows 11 ou Windows Server compatível.
- PowerShell 7.6 LTS ou posterior compatível.
- Python 3.11 ou posterior, em ambiente isolado e versionado.
- Pester 5 para os testes PowerShell.
- Hyper-V e OpenSSH apenas para métodos que usam o worker opcional.

O bootstrap nunca instala dependências automaticamente. Use `bootstrap/Test-NexusHost.ps1` para diagnosticar o host e registre separadamente qualquer instalação autorizada.

## Início rápido

```powershell
Import-Module .\powershell\NexusLab\NexusLab.psd1

Initialize-NexusLab `
  -EvidenceRoot 'E:\EvidenceVault' `
  -CaseRoot 'D:\NexusCases' `
  -ToolRoot 'C:\ProgramData\NexusLab\Tools' `
  -CreateRoots

New-NexusCase `
  -CaseId 'CASE-2026-0002' `
  -Authority '<referência da autoridade>' `
  -Scope '<escopo>' `
  -Question '<pergunta pericial>' `
  -Examiner '<operador>'
```

`Initialize-NexusLab` recusa raízes ausentes, sobrepostas ou dentro do repositório. `-CreateRoots` apenas cria diretórios; ACLs, BitLocker e controles organizacionais devem ser aplicados e verificados pelo administrador do laboratório.

## Componentes

- `powershell/NexusLab/`: cmdlets públicos e runner de processos sem shell.
- `python/nexus_lab/`: núcleo transacional e CLI JSON.
- `schemas/`: esquema SQLite e contratos JSON.
- `methods/`: method packs versionados e aprováveis.
- `tools/catalog.json`: capacidades, provedores e disposição Windows/Hyper-V.
- `.codex/skills/`: skills do agente; não concedem autorização.
- `tests/`: testes Python, Pester e fixtures exclusivamente sintéticas.
- `docs/`: arquitetura, operação, segurança, worker e referencial.

Consulte [arquitetura](docs/architecture.md), [operação](docs/operations.md), [segurança](docs/security.md), [worker Hyper-V](docs/hyperv-worker.md) e [validação](docs/validation.md).
