# P10 — SAST & Secrets summary

## Semgrep
- Команда запуска: `semgrep ci --config p/ci --config security/semgrep/rules.yml`.
- После удаления секретов из логов и перевода пользователей на хешированные env-пароли Semgrep возвращает 0 совпадений (`EVIDENCE/P10/semgrep.sarif`).
- Итог: ни в коде, ни в логах нет plaintext-паролей/JWT, правило `simpleblog-unsafe-safe_log-credentials` проходит без замечаний

## Gitleaks
- Конфиг `security/.gitleaks.toml` расширяет дефолт и добавляет allowlist для `EVIDENCE/P10/**`, учебного PAT `ghp_SAMPLE…` и AWS-шаблона `AKIAIOSFODNN7EXAMPLE` из playbook.
- Bootstrap-пароли вынесены в `.env`/`tests/conftest.py` и хешируются, поэтому текущее сканирование (`docker run ... detect --no-git`) создаёт пустой отчёт (`EVIDENCE/P10/gitleaks.json`) (до этого был непустой)
- При появлении новых ложных срабатываний добавляем их в allowlist с комментарием, чтобы сигнал не деградировал

## Follow-up
- Workflow `Security - SAST & Secrets` загружает SARIF и JSON артефакты (см. последнюю успешную job в Actions).
- После мерджа P10 скан проходит в каждом PR по путям `app/**`, `security/**`, `docs/security/**`, что покрывает изменения в коде и политиках.
