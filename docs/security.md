# Segurança da estação

- Use conta operacional padrão; eleve apenas para uma ação autorizada.
- Aplique ACL somente leitura no cofre e leitura/execução no catálogo de ferramentas.
- Proteja volumes com criptografia apropriada e mantenha chaves fora dos casos.
- Mantenha rede externa bloqueada durante exames que não a autorizem.
- Valide Authenticode, hash, origem e licença de cada binário; não atualize ferramentas durante um caso.
- Considere App Control for Business para allowlist. Teste em modo de auditoria antes de aplicar.
- PowerShell logging pode conter caminhos ou dados sensíveis. Restrinja acesso e retenção; não use transcrições como substituto dos registros do Nexus-Lab.
- Não crie exclusões de antivírus automaticamente. Documente qualquer interferência, quarentena ou exceção autorizada.

O runner não usa `Invoke-Expression`, shell intermediário ou argumentos concatenados. Saídas são gravadas em UTF-8 e registradas separadamente.

