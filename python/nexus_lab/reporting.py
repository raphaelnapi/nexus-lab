from __future__ import annotations

from datetime import datetime, timezone

from .config import LabConfig
from .database import CaseDatabase, new_id, utc_now
from .hashing import hash_file, safe_relative


def create_report(config: LabConfig, *, case_id: str, operator: str) -> dict[str, object]:
    database = CaseDatabase(config, case_id)
    connection = database.connect()
    try:
        case = dict(connection.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone())
        findings = [dict(row) for row in connection.execute("SELECT * FROM findings WHERE case_id=? ORDER BY created_at_utc", (case_id,))]
        statements = {
            finding["finding_id"]: [dict(row) for row in connection.execute(
                """SELECT s.*,fs.relationship FROM statements s
                   JOIN finding_support fs ON fs.statement_id=s.statement_id
                   WHERE fs.finding_id=? ORDER BY s.created_at_utc""",
                (finding["finding_id"],),
            )]
            for finding in findings
        }
        evidence = [dict(row) for row in connection.execute("SELECT evidence_id,logical_name,evidence_type,size_bytes,sha256,sha512,verified_at_utc FROM evidence_items WHERE case_id=? ORDER BY evidence_id", (case_id,))]
        version = connection.execute("SELECT COALESCE(MAX(version),0)+1 FROM reports WHERE case_id=?", (case_id,)).fetchone()[0]
    finally:
        connection.close()
    report_id = f"REPORT-{case_id}"
    report_version_id = f"{report_id}-V{version}"
    lines = [
        f"# Relatório técnico — {case_id}", "",
        f"Versão: {version}", f"Gerado por: {operator}", f"Gerado em UTC: {utc_now()}", "",
        "## Autoridade, escopo e pergunta", "",
        f"- Autoridade: {case['authority']}", f"- Escopo: {case['scope']}", f"- Pergunta: {case['question']}", "",
        "## Evidências", "",
    ]
    for item in evidence:
        lines.append(f"- {item['evidence_id']} — {item['logical_name']} ({item['evidence_type']}), SHA-256 `{item['sha256']}`")
    lines.extend(["", "## Achados", ""])
    if not findings:
        lines.append("Nenhum achado registrado.")
    for finding in findings:
        lines.extend([f"### {finding['finding_id']} — {finding['title']}", ""])
        for statement in statements[finding["finding_id"]]:
            locator = f"; fonte: {statement['source_locator']}" if statement["source_locator"] else ""
            lines.append(f"- **{statement['state']} / {statement['relationship']}:** {statement['text']}{locator}")
        if finding["limitations"]:
            lines.append(f"- **Limitações:** {finding['limitations']}")
        lines.append("")
    lines.extend([
        "## Limitações gerais", "",
        "Este relatório reflete apenas os registros presentes no banco do caso. Campos ausentes não foram reconstruídos por plausibilidade.", "",
        "A estrutura do Nexus-Lab não constitui certificação, acreditação ou garantia de admissibilidade jurídica.", "",
    ])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = database.case_dir / "derived" / "reports" / f"{case_id}-report-v{version}-{stamp}.md"
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    digest = hash_file(path)
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO reports(report_version_id,report_id,case_id,version,relative_path,sha256,created_by,created_at_utc) VALUES(?,?,?,?,?,?,?,?)",
            (report_version_id, report_id, case_id, version, safe_relative(path, database.case_dir), digest.sha256, operator, utc_now()),
        )
        database.append_audit(connection, actor=operator, action="report-created", entity_type="report", entity_id=f"{report_id}:v{version}", payload={"relative_path": safe_relative(path, database.case_dir), "sha256": digest.sha256})
    return {"report_id": report_id, "version": version, "path": str(path), "sha256": digest.sha256}

