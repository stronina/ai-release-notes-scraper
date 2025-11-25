# AI Release Notes Scraper

Скрипт собирает заметки о релизах ИИ-сервисов и сохраняет их в Airtable или CSV. В качестве примера есть парсер страницы ChatGPT Release Notes. Добавляйте новые функции-"fetchers" по аналогии, чтобы собирать данные с других сайтов.

## Запуск

Установите зависимости (лучше в виртуальном окружении):

```bash
pip install -r requirements.txt
```

### Airtable

Для записи в Airtable нужны переменные окружения:

- `AIRTABLE_TOKEN`
- `AIRTABLE_BASE`
- `AIRTABLE_TABLE`

### Команды

Собрать все источники и отправить в Airtable, а также сделать CSV-копию:

```bash
python scrape.py --csv releases.csv
```

Собрать только ChatGPT и не трогать Airtable (полезно для локальной проверки):

```bash
python scrape.py --sources chatgpt --skip-airtable --csv chatgpt.csv
```

Если Airtable не настроен, скрипт автоматически пропустит загрузку и просто сохранит CSV, если путь указан.

## Как добавить новый источник

1. Напишите функцию `fetch_<название>()`, которая возвращает список словарей с ключами:
   - `Product`
   - `Feature name`
   - `Description`
   - `Release date` (ISO-формат `YYYY-MM-DD`)
   - `Source URL`
   - `Source page`
   - `External ID` (уникальный идентификатор для дедупликации)
2. Добавьте функцию в словарь `FETCHERS` в `scrape.py`.
3. Запустите с `--sources <название>` или оставьте пустым, чтобы собирать всё.

Так можно быстро подключать любые страницы релизов без дополнительной настройки окружения.
