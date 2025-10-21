# STRIDE — Simple Blog

На 7 ключевых потоков отмечены угрозы STRIDE, меры контроля и ссылки на NFR-issues.

| Поток / Элемент | Угроза (STRIDE) | Риск | Контроль | Ссылка на NFR | Проверка / Артефакт |
|-----------------|-----------------|------|----------|---------------|------------------|
| F1 /login       | S: Spoofing     | R1   | MFA + rate-limit | [NFR-01](https://github.com/hse-secdev-2025-fall/course-project-vilina4ka/issues/16) | e2e + ZAP baseline |
| F1 /login       | T: Tampering    | R2   | TLS + JWT проверка | [NFR-01](https://github.com/hse-secdev-2025-fall/course-project-vilina4ka/issues/16) | CI проверка сертификатов |
| F2 /posts       | I: Tampering    | R3   | owner-only access, валидация | [NFR-02](https://github.com/hse-secdev-2025-fall/course-project-vilina4ka/issues/17), [NFR-04](https://github.com/hse-secdev-2025-fall/course-project-vilina4ka/issues/19) | Unit + интеграционные тесты |
| F2 /posts       | R: Repudiation  | R4   | логирование действий | [NFR-07](https://github.com/hse-secdev-2025-fall/course-project-vilina4ka/issues/22) | CI логирование |
| F7 /DB          | D: Disclosure   | R5   | шифрование данных на уровне БД | [NFR-07](https://github.com/hse-secdev-2025-fall/course-project-vilina4ka/issues/22) | Тест шифрования данных |
| F6 /Core        | E: Elevation    | R6   | RBAC + проверки owner | [NFR-02](https://github.com/hse-secdev-2025-fall/course-project-vilina4ka/issues/17) | Unit тесты API |
| F3 /posts       | T: Tampering    | R7   | Валидация входных данных | [NFR-04](https://github.com/hse-secdev-2025-fall/course-project-vilina4ka/issues/19) | Интеграционные тесты |
| F3 /posts       | I: Information Disclosure | R8 | Только авторизованный доступ | [NFR-07](https://github.com/hse-secdev-2025-fall/course-project-vilina4ka/issues/22) | e2e тесты |
