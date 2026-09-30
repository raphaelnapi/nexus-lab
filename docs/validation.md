# Validação

Execute no repositório:

```powershell
python -m unittest discover -s tests/python -v
Invoke-Pester -Path tests/powershell
```

Os testes usam diretórios temporários e dados sintéticos. Eles cobrem limites de caminho, hashing, esquema, ledger, autorização, migração, codificação e contratos dos cmdlets. Testes de Hyper-V ficam marcados como integração e devem ser executados apenas em host preparado.

Antes de admitir uma ferramenta, registre versão, origem, assinatura/hash, licença, comando de versão e resultado sobre fixture conhecida. Resultados materiais exigem validação proporcional com artefato de origem ou parser independente.

