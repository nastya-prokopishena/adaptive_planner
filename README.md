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

У проєкті реалізовано комплексне тестування backend-частини системи Adaptive Planner.

### Реалізовані типи тестування

* unit tests
* integration tests
* security tests
* performance tests
* benchmark tests
* coverage analysis
* static code analysis

Для тестування та аналізу використовуються:

* `pytest`
* `pytest-cov`
* `pytest-benchmark`
* `Bandit`
* `SonarQube`
* `Locust`

---

### Запуск тестів

```bash
python -m pytest
```

### Запуск coverage analysis

```bash
python -m pytest --cov=backend --cov-report=term-missing --cov-report=html
```

---

### Поточні результати тестування

```text
398 passed
83% total backend coverage
0 critical security issues
```

---

### Benchmark тестування

У проєкті реалізовано benchmark-тестування для:

* NLP-аналізу задач
* AI-обробки розкладу
* алгоритмів автоматичного планування
* генерації candidate slots

---

### Performance тестування

Для навантажувального тестування використовується `Locust`.

Тестування перевіряє:

* стабільність REST API
* одночасну роботу користувачів
* час відповіді backend
* навантаження під час AI/NLP-аналізу

---

### Security testing

Для аналізу безпеки використовуються:

* security pytest tests
* Bandit static analysis
* перевірка authentication та protected routes
* перевірка XSS та SQL Injection scenarios

---

## 🚀 CI/CD

У проєкті реалізовано автоматизовані CI/CD workflows за допомогою GitHub Actions.

Після кожного `push` або `pull_request` система автоматично запускає перевірку якості коду, безпеки, тестування та збірки Docker-образу.

### Реалізовані workflows

| Workflow                  | Призначення |
|---------------------------|-------------|
| `Backend CI`              | Автоматичний запуск `black`, `isort`, `flake8` та `pytest` |
| `Backend Security Scan`   | Аналіз безпеки backend-коду за допомогою `Bandit` |
| `Docker Build Check`      | Перевірка коректності збірки Docker image |
| `SonarQube Analysis`      | Аналіз якості коду, пошук potential bugs, code smells та проблем підтримуваності |

CI/CD пайплайн забезпечує:
- автоматичне тестування backend-частини;
- контроль стилю коду;
- перевірку безпеки застосунку;
- перевірку Docker-конфігурації;
- контроль якості коду через SonarQube;
- стабільність процесу розгортання.

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

### Головна сторінка Adaptive Planner

Головна сторінка системи містить календар подій, список найближчих задач, статистику активності користувача та швидкий доступ до основних функцій застосунку. Інтерфейс реалізований з використанням React та FullCalendar.

![Головна сторінка Adaptive Planner](frontend/dist/images/dashboard-main.png)

---

### Інтерфейс імпорту розкладу з AI-аналізом

Сторінка імпорту розкладу дозволяє завантажувати PDF, DOCX, Excel, CSV, TXT та зображення розкладу. Після завантаження файл проходить AI/OCR-аналіз для автоматичного визначення пар, викладачів, часу занять та навчальних груп.

![Імпорт розкладу](frontend/dist/images/schedule-import.png)

---

### Сторінка AI-аналізу навчальних файлів

Модуль AI/NLP-аналізу використовується для автоматичного визначення типу задачі, складності, тривалості та ключових слів на основі тексту лабораторних або практичних робіт.

![AI аналіз файлів](frontend/dist/images/task-analysis.png)

---

### Попередній перегляд задач після AI/NLP-аналізу

Після аналізу система автоматично формує preview задачі із запропонованим дедлайном, оцінкою складності, типом задачі та орієнтовною тривалістю виконання.

![Preview задач](frontend/dist/images/task-preview.png)

---

### Система керування навчальними задачами

Сторінка задач дозволяє переглядати задачі за предметами, змінювати статуси виконання, редагувати дедлайни та відстежувати прогрес навчальної діяльності.

![Керування задачами](frontend/dist/images/tasks-management.png)

---

### Панель аналітики продуктивності користувача

Модуль аналітики візуалізує навантаження користувача, продуктивність, складність задач та статистику виконання за допомогою графіків і діаграм.

![Аналітика](frontend/dist/images/analytics-dashboard.png)

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

У процесі розробки проєкту були використані сучасні підходи до проєктування вебзастосунків, AI/ML-інтеграцій, REST API, контейнеризації, автоматизованого тестування та CI/CD.

### 📚 Наукова та професійна література

1. Мартин Р. *Чиста архітектура: Мистецтво розроблення програмного забезпечення*. Фабула, 2023.
2. Фаулер М. *Рефакторинг: поліпшення дизайну існуючого коду*. Діалектика, 2021.
3. Goodfellow I., Bengio Y., Courville A. *Deep Learning*. MIT Press, 2016.

---

### 🌐 Frontend технології

- React — бібліотека для побудови користувацьких інтерфейсів  
  https://react.dev

- Vite — інструмент збірки frontend-застосунків  
  https://vite.dev

- React Router — бібліотека маршрутизації React-застосунків  
  https://reactrouter.com

- Axios — HTTP-клієнт для взаємодії з REST API  
  https://axios-http.com

- FullCalendar — бібліотека інтерактивного календаря  
  https://fullcalendar.io

- Recharts — бібліотека побудови графіків та аналітики  
  https://recharts.org

---

### 🐍 Backend технології та Python-екосистема

- Flask — Python веб-фреймворк  
  https://flask.palletsprojects.com

- Python Documentation  
  https://docs.python.org/3/

- Jinja2 — шаблонізатор Python  
  https://jinja.palletsprojects.com

- Flask-SQLAlchemy — ORM інтеграція SQLAlchemy з Flask  
  https://flask-sqlalchemy.palletsprojects.com

- Flask-Migrate — інструмент міграцій бази даних  
  https://flask-migrate.readthedocs.io

- SQLAlchemy — ORM для роботи з PostgreSQL  
  https://www.sqlalchemy.org

- PostgreSQL — система керування базами даних  
  https://www.postgresql.org

- Redis — система кешування та збереження тимчасових даних  
  https://redis.io

---

### 🤖 AI / ML / Data Processing

- OpenAI API — AI/NLP обробка тексту та аналіз розкладу  
  https://platform.openai.com/docs/

- Scikit-learn — бібліотека машинного навчання  
  https://scikit-learn.org

- NumPy — бібліотека математичних обчислень  
  https://numpy.org

- Pandas — бібліотека аналізу та обробки даних  
  https://pandas.pydata.org

- OpenCV — бібліотека комп’ютерного зору  
  https://opencv.org

- Pdfplumber — обробка PDF-файлів  
  https://pypi.org/project/pdfplumber/

- python-docx — обробка DOCX документів  
  https://pypi.org/project/python-docx/

- SerpApi — API для роботи з пошуковими системами  
  https://serpapi.com

---

### 📅 Інтеграції та API

- Google Calendar API — синхронізація подій та календаря  
  https://developers.google.com/calendar

- Swagger/OpenAPI — документація REST API  
  https://swagger.io

---

### 🐳 DevOps та CI/CD

- Docker — контейнеризація застосунку  
  https://docs.docker.com

- GitHub Actions — автоматизація CI/CD pipeline  
  https://github.com/features/actions

---

### 🧪 Тестування та контроль якості

- Pytest — автоматизоване тестування Python-застосунків  
  https://docs.pytest.org

- Locust — навантажувальне тестування  
  https://locust.io

- SonarQube — аналіз якості та безпеки коду  
  https://www.sonarqube.org
