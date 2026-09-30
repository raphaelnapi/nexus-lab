# Worker Linux Hyper-V

O worker é opcional e não é um fallback silencioso.

## Perfil obrigatório

- Host com Hyper-V e cmdlets disponíveis.
- Imagem-base versionada e imutável; disco diferencial descartável por job.
- Switch interno sem gateway, NAT ou rota externa.
- SSH/SFTP limitado ao host e chave dedicada ao laboratório.
- Ferramentas e versões fixadas na imagem; manutenção fora de exames.
- Entrada copiada de uma working copy, nunca montada diretamente do cofre.
- SHA-256 verificado no host, no guest e após o retorno.
- Saída transferida e registrada antes de encerrar o job.

`bootstrap/Test-NexusHyperV.ps1` faz somente diagnóstico. Provisionamento da VM, rede, chaves, instalação e descarte de discos requerem procedimento administrativo separado e autorização explícita.

