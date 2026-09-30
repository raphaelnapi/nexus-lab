# Operação

## Ciclo do caso

1. Configure raízes externas e valide o host.
2. Crie o caso com autoridade, escopo, pergunta e responsável.
3. Registre a evidência no local; o núcleo calcula SHA-256 e SHA-512 sem escrever na origem.
4. Registre a autorização e crie uma cópia de trabalho verificada.
5. Selecione um method pack e registre limites e validade com `Approve-NexusMethod`.
6. Execute com `Invoke-NexusMethod`; qualquer diferença de definição ou parâmetros bloqueia o run.
7. Registre artefatos, timestamps e afirmações com estado epistêmico.
8. Gere relatórios e manifestos versionados; crie checkpoints do ledger.

## Aprovações por método

Uma aprovação identifica caso, método, versão e hash do pack, aprovador, validade e parâmetros delimitados. Ela não autoriza implicitamente instalação, rede externa, driver, montagem, aquisição, dispositivo ou exportação. Alterações nesses elementos exigem uma autorização adequada e um pack compatível.

Antes de executar, copie e preencha `tools/validated-tools.example.json` como `<tool-root>/validated-tools.json`. O runner exige que o executável esteja fisicamente abaixo do `tool-root` e que seu SHA-256 corresponda ao manifesto. Descoberta pelo `PATH` é apenas diagnóstico, nunca validação.

## Falhas

Execuções são registradas antes do processo. Falhas, timeouts e retries permanecem no banco. Não edite uma execução: crie outra com `retry_of`. Hash divergente, ledger inválido ou contexto ambíguo exige interrupção.

