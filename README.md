# authorization-jwt

Асинхронное REST API на FastAPI с ролевой моделью доступа (admin, moderator, editor, user), JWT access/refresh токенами, мягким удалением и иерархией подчинённых.



```bash
форматировать readme помогала нейронка, но код мой.




```


Работать с виртуальным окружением. Установить зависимости. 
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

## 🚀 Стек

- Python 3.14
- FastAPI
- SQLAlchemy 2.0 (async) + aiosqlite
- JWT
- passlib[bcrypt]
- hashlib
- Pydantic

---

## 📦 Установка и запуск

Создайте `.env` в корне проекта:

```ini
ADMIN_PASSWORD="admin_password"
ADMIN_EMAIL="admin@admin.admin"
ADMIN_NAME="admin"
ADMIN_SURNAME="admin"
ADMIN_PATRONYMIC="admin"
DATA_BASE_SETUP_KEY="admin_setup_db_key_dont_show_to_anyone"

JWT_SECRET_KEY="admin_jwt_key_dont_show_to_anyone"
```

В коде запуск uvicorn происходит с флагом --reload. Это очень удобно при локальной разработке
Запуск python из КОРНЯ ПРОКТА:

```bash
python -m app.main
```

После запуска один раз выполните инициализацию. Создастся БД м админ. Данные админа в `.env`.
Можете этого не делать, таблица создастся сама (asynccontextmanager) с нужными полями, но она будет пуста. 

```
curl -X POST "http://localhost:8000/service/setup_database?setup_db_key=mysetupkey"
```

Ключ сравнится с тем, что лежит в .env файле - DATA_BASE_SETUP_KEY. 

---

## 🧱 В бд хранится 2 таблицы

### `users`

| Поле            | Тип                         |
|----------------|-----------------------------|
| id             | int (PK)                    |
| supervisor_id  | int (FK → users.id, nullable) |
| role           | Enum(admin,moderator,editor,user) |
| user_email     | string (unique)             |
| password       | string (bcrypt)             |
| is_active      | bool                        |
| user_name      | string                      |
| user_surname   | string                      |
| user_patronymic| string                      |

### `refresh_tokens`

| Поле                | Тип            |
|--------------------|----------------|
| id                 | int (PK)       |
| user_id            | int (FK)       |
| expires            | datetime (UTC) |
| refresh_hash_token | string (SHA256)|

---

## 🎯 Ролевая модель доступа

| Роль       | Что может                                                                                                                                 |
|------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| `user`     | – регистрация, логин, логаут<br>– просмотр/изменение своих ФИО<br>– смена пароля<br>– мягкое удаление себя<br>– **не** может назначать других |
| `editor`   | – всё из `user`<br>– назначать себе свободных `user` (`/users/free-users`, `/users/{id}/assign-to-me`)<br>– список своих подчинённых (`/users/my-users`) |
| `moderator`| – всё из `user`<br>– назначать себе свободных `editor`<br>– просмотр своих подчинённых (`editor`)                            |
| `admin`    | – доступ к `/admin/users/{target_id}`<br>– редактирование любых полей (email, роль, активность, начальник)<br>– **не** может деактивировать себя или менять свою роль<br>– не назначает подчинённых другим админам и админами никого не назначает |

---

## 🏗 Архитектура

- **Pydantic** – валидация входных данных и сериализация ответов (схемы в `schemas.py`).
- **SQLAlchemy 2.0** – асинхронные модели (`models.py`) и работа с БД.
- **FastAPI Depends** – dependency injection для получения текущего пользователя (`get_current_user`), сессии БД (`SessionDep`) и других зависимостей.

---

## 🌐 Роутеры API

### Auth (`/auth`)

| Метод | Эндпоинт            | Описание                          |
|-------|---------------------|-----------------------------------|
| POST  | `/auth/registration`| Регистрация (role = user/editor)  |
| POST  | `/auth/login`       | Вход → access + refresh токены    |
| POST  | `/auth/refresh`     | Обновить access по refresh        |
| POST  | `/auth/logout`      | Выход (удаляет все refresh токены)|

### Profile (`/profile`)

| Метод  | Эндпоинт                     | Описание                   |
|--------|------------------------------|----------------------------|
| GET    | `/profile`                   | Получить свой профиль       |
| PATCH  | `/profile`                   | Изменить свои ФИО           |
| DELETE | `/profile`                   | Мягкое удаление аккаунта    |
| POST   | `/profile/change-password`   | Смена пароля, удаление refresh|

### Users (editor/moderator/admin)

| Метод | Эндпоинт                     | Описание                                                      |
|-------|------------------------------|---------------------------------------------------------------|
| GET   | `/users/free-users`          | Незанятые (editor → user, moderator → editor)                 |
| PATCH | `/users/{id}/assign-to-me`   | Назначить пользователя себе (с проверкой роли)                |
| GET   | `/users/my-users`            | Список моих прямых подчинённых                                |
| GET   | `/admin/users/{id}`          | Получить любого пользователя                                  |
| PATCH | `/admin/users/{id}`          | Редактировать: email, role, is_active, supervisor_id, ФИО     |

### Service (`/service`)

| Метод | Эндпоинт                     | Описание                                                      |
|-------|------------------------------|---------------------------------------------------------------|
| POST  | `/service/setup_database`    | Пересоздать БД + создать админа (требуется ключ из .env)      |

---

## 📋 Примеры запросов

### Регистрация

```bash
curl -X POST http://localhost:8000/auth/registration \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "ivan@example.com",
    "user_name": "Иван",
    "user_surname": "Петров",
    "user_patronymic": "Сергеевич",
    "password": "securepass",
    "password_repeat": "securepass",
    "role": "user"
  }'
```

### Логин

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user_email": "ivan@example.com", "password": "securepass"}'
```

Ответ:

```json
{
  "id": 2,
  "user_email": "ivan@example.com",
  "user_name": "Иван",
  "user_surname": "Петров",
  "user_patronymic": "Сергеевич",
  "is_active": true,
  "role": "user",
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "refresh_token": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Профиль (с access токеном)

```bash
curl -X GET http://localhost:8000/profile \
  -H "Authorization: Bearer <access_token>"
```

### Назначение редактором

```bash
curl -X PATCH http://localhost:8000/users/2/assign-to-me \
  -H "Authorization: Bearer <editor_access_token>"
```

### Админ деактивирует пользователя

```bash
curl -X PATCH http://localhost:8000/admin/users/2 \
  -H "Authorization: Bearer <admin_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

---

## ⚙️ Детали реализации

- **Access токен** живёт 5 минут, **refresh** – 30 минут (настраивается в `tokens_functions.py`).
- При смене пароля, деактивации или смене роли все refresh токены пользователя удаляются – принудительный выход на всех устройствах.
- Защита от перебора email при регистрации: одинаковая задержка и ответ (не раскрывает существование аккаунта).
- Все даты в UTC.
- Ошибки: 401 – неавторизован, 403 – недостаточно прав, 500 – глобальный обработчик.

---

## 🛠 Production

- Заменить SQLite на PostgreSQL (изменить `DATABASE_URL` в `database.py`)
- Хранить секреты в переменных окружения

---

## 📄 Лицензия

MIT
