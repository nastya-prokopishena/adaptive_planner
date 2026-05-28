# 📘 Adaptive Planner

> Вебзастосунок для адаптивного планування навчальних задач, розкладу, дедлайнів і продуктивності студента з використанням AI/ML, Google Calendar, Docker, CI/CD та автоматизованого тестування.

---

## 👤 Автор

* **ПІБ**: Прокопішена Анастасія
* **Група**: ФеП-42
* **Керівник**: [вказати ПІБ керівника]
* **Дата виконання**: 2026

---

## 📌 Загальна інформація

* **Тип проєкту**: Вебзастосунок
* **Frontend**: React, JavaScript, CSS
* **Backend**: Python, Flask
* **База даних**: PostgreSQL
* **Кешування / додаткові сервіси**: Redis
* **AI/ML**: OpenAI API, ML-моделі для оцінки складності задач і прогнозування дедлайнів
* **Інтеграції**: Google Calendar API
* **DevOps**: Docker, Docker Compose, GitHub Actions
* **Тестування**: pytest, coverage, Locust, Bandit, flake8, black, isort

---

## 🧠 Опис функціоналу

* 🔐 Реєстрація та авторизація користувачів
* 📅 Створення, редагування, видалення та пошук подій
* ✅ Створення і керування навчальними задачами
* 📌 Автоматичне планування задач у вільні часові слоти
* 🧠 NLP-аналіз тексту завдань
* 🤖 AI-імпорт розкладу з файлів, таблиць і зображень
* 📊 Аналітика продуктивності користувача
* 🧮 ML-оцінка складності задач
* ⏰ Автоматичне прогнозування дедлайнів
* 🔁 Підтримка повторюваних подій
* 🌐 REST API
* 📘 Swagger/OpenAPI документація
* 🧪 Unit, integration, security та performance tests
* 🚀 CI/CD pipeline через GitHub Actions

---

## 🧱 Опис основних класів / файлів

| Клас / Файл                                          | Призначення                                                                             |
| ---------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `backend/app/__init__.py`                            | Створення Flask-застосунку, підключення CORS, Swagger, routes та error handlers         |
| `backend/app/routes/`                                | REST API маршрути для авторизації, подій, задач, аналітики та імпорту розкладу          |
| `backend/application/`                               | Application layer: бізнес-логіка, AI/NLP/ML сервіси, імпорт файлів                      |
| `backend/domain/`                                    | Domain layer: сутності, інтерфейси, доменні сервіси, патерни                            |
| `backend/infrastructure/`                            | Infrastructure layer: база даних, Google Calendar adapter, ML adapters, file extractors |
| `backend/domain/factories/file_extractor_factory.py` | Factory Method для вибору extractor залежно від типу файлу                              |
| `backend/infrastructure/google_calendar_adapter.py`  | Adapter для інтеграції з Google Calendar API                                            |
| `backend/domain/services/auto_planner.py`            | Логіка автоматичного планування задач                                                   |
| `backend/domain/recurrence.py`                       | Логіка повторюваних подій                                                               |
| `backend/tests/`                                     | Unit, integration, security та performance tests                                        |
| `.github/workflows/ci.yml`                           | CI pipeline: black, isort, flake8, pytest                                               |
| `.github/workflows/security.yml`                     | Security scan через Bandit                                                              |
| `.github/workflows/docker-build.yml`                 | Перевірка Docker build                                                                  |
| `locustfile.py`                                      | Performance/load testing через Locust                                                   |

---

## 🧩 Архітектура та патерни

У проєкті використано багаторівневу архітектуру з розділенням відповідальності:

* **Presentation/API layer** — Flask routes
* **Application layer** — сервіси бізнес-логіки
* **Domain layer** — доменні моделі, інтерфейси, правила
* **Infrastructure layer** — база даних, зовнішні API, ML, file extractors

Використані патерни:

* **Factory Method** — вибір file extractor залежно від формату файлу
* **Adapter** — інтеграція Google Calendar та ML-моделей
* **Strategy** — різні стратегії обробки файлів і планування
* **Repository** — доступ до даних користувача
* **Service Layer** — винесення бізнес-логіки з routes

---

## ▶️ Як запустити проєкт з нуля

### 1. Клонування репозиторію

```bash
git clone https://github.com/nastya-prokopishena/adaptive_planner.git
cd adaptive_planner
```

### 2. Створення віртуального середовища

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux / macOS:

```bash
source .venv/bin/activate
```

### 3. Встановлення залежностей

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Створення `.env`

```env
FLASK_ENV=development
SECRET_KEY=dev-secret-key
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/adaptive_planner
REDIS_HOST=localhost
REDIS_PORT=6379
OPENAI_API_KEY=your_openai_key
OPENAI_SCHEDULE_MODEL=gpt-4o
GOOGLE_CLIENT_SECRET_FILE=backend/infrastructure/credentials.json
GOOGLE_REDIRECT_URI=http://localhost:5000/callback
```

### 5. Запуск через Docker

```bash
docker compose up --build
```

### 6. Локальний запуск backend

```bash
python run.py
```

---

## 📘 Swagger / OpenAPI

Після запуску backend документація API доступна за адресою:

```text
http://localhost:5000/swagger/
```

OpenAPI JSON:

```text
http://localhost:5000/openapi.json
```

---

## 🔌 API приклади

### Авторизація

**POST `/auth/login`**

```json
{
  "email": "user@example.com",
  "password": "password"
}
```

---

### Події

**GET `/api/events`**

Отримання списку подій користувача.

**POST `/api/events`**

```json
{
  "title": "Лабораторна робота",
  "start": "2026-05-28T10:00:00",
  "end": "2026-05-28T11:30:00"
}
```

---

### Задачі

**GET `/api/tasks`**

Отримання списку задач.

**POST `/api/tasks`**

```json
{
  "title": "Підготувати звіт",
  "description": "Оформити лабораторну роботу",
  "priority": "medium",
  "task_type": "laboratory"
}
```

---

### AI-імпорт розкладу

**POST `/api/schedule-import/preview`**

Використовується для попереднього аналізу розкладу з файлу або тексту.

---

## 🧪 Тестування

У проєкті реалізовано:

* unit tests
* integration tests
* security tests
* performance tests
* coverage report

Запуск тестів:

```bash
python -m pytest
```

Запуск coverage:

```bash
python -m pytest --cov=backend --cov-report=term-missing --cov-report=html
```

Поточний результат:

```text
104 automated tests
53% backend coverage
```

---

## 🚀 CI/CD

У проєкті реалізовано GitHub Actions workflows:

| Workflow                | Призначення                         |
| ----------------------- | ----------------------------------- |
| `Backend CI`            | Запуск black, isort, flake8, pytest |
| `Backend Security Scan` | Перевірка backend через Bandit      |
| `Docker Build Check`    | Перевірка збірки Docker image       |

CI/CD автоматично запускається після кожного `push` або `pull_request`.

---

## 📈 Performance testing

Для навантажувального тестування використано Locust.

Запуск:

```bash
locust
```

Після запуску відкрити:

```text
http://localhost:8089
```

Приклад тесту:

```text
Users: 20
Ramp up: 5
Host: http://localhost:5000
```

Результати базового тестування:

```text
RPS: приблизно 12–13 запитів/сек
Median response time: приблизно 10–15 ms
95th percentile: приблизно 30–40 ms
Failures: 0%
```

---

## 🖱️ Інструкція для користувача

1. Зареєструватися або увійти в систему.
2. Додати навчальні події або імпортувати розклад.
3. Створити задачі вручну або через AI/NLP-аналіз.
4. Використати автоматичне планування для пошуку вільного часу.
5. Переглядати аналітику продуктивності.
6. За потреби синхронізувати події з Google Calendar.

---

## 📷 Приклади / скриншоти

Рекомендовано додати у папку:

```text
screenshots/
```

Скріншоти:

* головна сторінка;
* dashboard;
* календар;
* імпорт розкладу;
* Swagger UI;
* GitHub Actions;
* Locust performance test;
* coverage report.

---

## 🧪 Проблеми і рішення

| Проблема                  | Рішення                                                                                   |
| ------------------------- | ----------------------------------------------------------------------------------------- |
| `ModuleNotFoundError`     | Перевірити встановлення залежностей через `pip install -r requirements.txt`               |
| CI падає на `black`       | Запустити `black backend` локально і зробити commit                                       |
| CI падає на `flake8`      | Запустити `flake8 backend` та виправити lint-помилки                                      |
| Swagger не відкривається  | Перевірити, чи встановлено `flasgger` і чи підключено Swagger у `backend/app/__init__.py` |
| Locust показує failures   | Перевірити, чи не тестуються очікувані 401/400 як помилки                                 |
| Google Calendar не працює | Перевірити `credentials.json` і змінні середовища                                         |

---

## 🧾 Використані джерела / література

* Flask documentation
* React documentation
* PostgreSQL documentation
* Redis documentation
* Docker documentation
* GitHub Actions documentation
* Pytest documentation
* Swagger / OpenAPI documentation
* SonarQube documentation
* Locust documentation
* OpenAI API documentation
* Google Calendar API documentation
