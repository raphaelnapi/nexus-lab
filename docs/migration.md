# Migração do legado

`Invoke-NexusMigrationPreview` abre o SQLite legado em modo somente leitura, calcula seu SHA-256 e informa contagens e campos bloqueantes. Não cria ou altera casos.

`Invoke-NexusMigration` cria um caso v2 novo no `case-root`, importa somente campos sustentados pelo legado e registra o hash da origem. O banco antigo, os manifestos e as evidências permanecem intactos. Nesta versão, evidências e eventos de custódia são importados; demais tabelas permanecem no legado até haver um mapeamento sem perda semântica.

Uma migração já existente é recusada. Campos obrigatórios ausentes são bloqueadores; não são preenchidos por inferência.

