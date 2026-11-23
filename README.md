# Помощник студента

Чат-помощник на Streamlit. Сначала выбираешь, на чём он работает (модель и ключ), потом отвечаешь на 12 вопросов о себе. После этого он объясняет темы под тебя, а режим над строкой ввода переключает, что именно делать: объяснить, простыми словами, с примером, конспект, проверить тебя или составить план.

## Что внутри

- Streamlit — интерфейс и чат со стримингом ответа
- requests — запросы к любому OpenAI-совместимому API
- Провайдеры: OpenRouter, OpenAI, Groq, DeepSeek, Google Gemini, Mistral, Together и «Свой API» (любой Base URL + модель)

## Запуск

```bash
pip install -r requirements.txt
streamlit run app.py
```

Ключ можно ввести в интерфейсе или положить в `.streamlit/secrets.toml` (пример — `secrets.toml.example`). Ключ из интерфейса живёт только в памяти сессии.

## Онлайн (Streamlit Community Cloud)

1. Зайти на share.streamlit.io и войти через GitHub.
2. New app → этот репозиторий, ветка `main`, файл `app.py`.
3. По желанию в Advanced settings → Secrets добавить `OPENROUTER_API_KEY = "..."`.

Названия бесплатных моделей на OpenRouter меняются, актуальный список на openrouter.ai/models (фильтр Free). Модель можно вписать вручную.
