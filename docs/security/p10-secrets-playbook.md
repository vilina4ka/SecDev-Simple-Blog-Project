# P10 — SAST & Secrets Playbook

## Обязательные артефакты
- `EVIDENCE/P10/semgrep.sarif` — SARIF-отчёт Semgrep. Генерируется профилем `p/ci` + кастомные правила из `security/semgrep/rules.yml`.
- `EVIDENCE/P10/gitleaks.json` — JSON-отчёт Gitleaks c использованием `security/.gitleaks.toml`.
- `EVIDENCE/P10/sast_summary.md` — краткий разбор находок и действий.

## Проводим сканы
- Semgrep (в Docker):
  ```
  docker run --rm -v "$PWD:/src" returntocorp/semgrep:latest \
    semgrep ci --config p/ci --config /src/security/semgrep/rules.yml \
      --sarif --output /src/EVIDENCE/P10/semgrep.sarif --metrics=off || true
  ```
- Gitleaks (в Docker):
  ```
  docker run --rm -v "$PWD:/repo" zricethezav/gitleaks:latest \
    detect --no-banner --config=/repo/security/.gitleaks.toml \
      --source=/repo --report-format=json \
      --report-path=/repo/EVIDENCE/P10/gitleaks.json --no-git || true
  ```

## Политика реагирования
- **Semgrep**: high/critical — фиксим до мерджа, medium — создаём issue с ссылкой на SARIF, low — документируем в summary.
- **Gitleaks**: всё, что похоже на реальные секреты, удаляем из кода. False positive попадает в `[allowlist]` с комментарием, чтобы не «заглушать» всё подряд.
- Отдельные совпадения связываем с задачами в backlog (см. summary), чтобы было видно, кто отвечает за remediation.
- Глобальный allowlist в `security/.gitleaks.toml` прикрывает `EVIDENCE/P10/**`, `ghp_SAMPLE...` и публичный AWS `AKIAIOSFODNN7EXAMPLE`, чтобы артефакты и обучающие примеры не портили сигнал.

## Что делает workflow
1. Запускается на `push`/`pull_request` по изменениям в коде и security-файлах.
2. Выполняет Semgrep и Gitleaks в Docker-контейнерах, кладет отчеты в `EVIDENCE/P10`.
3. Загружает SARIF в GitHub Code Scanning и публикует оба файла артефактами `p10-security-artifacts`.
4. Workflow не ломает пайплайн, но оставляет красный статус для job, если вручную убрать `|| true`.
