import os

import streamlit as st

from llm import PROVIDERS, LLMError, stream_chat

st.set_page_config(page_title="Помощник студента", page_icon="🎓", layout="centered")

# ---------------------------------------------------------------- вопросы ---

QUESTIONS = [
    ("name", "Привет! Я помощник по учёбе. Для начала — как тебя зовут?", []),
    ("level", "Где учишься?", ["Школа", "Колледж", "Университет", "Учусь сам(а)"]),
    ("field", "Что именно изучаешь? Класс, курс или специальность — как тебе удобно.", []),
    ("hard", "Какие предметы сейчас даются тяжелее всего?", []),
    (
        "urgent",
        "Что горит прямо сейчас? Экзамен, сдача, контрольная — напиши с датой, если она есть.",
        ["Пока ничего срочного"],
    ),
    (
        "style",
        "Как тебе проще всего понимать новое?",
        ["На примерах", "По шагам", "Через схемы и аналогии", "Коротко и по делу"],
    ),
    ("depth", "Насколько подробно объяснять?", ["Коротко", "Средне", "Подробно, со всеми нюансами"]),
    (
        "time",
        "Сколько времени в день ты реально готов(а) тратить на учёбу?",
        ["До 30 минут", "1–2 часа", "3 часа и больше"],
    ),
    ("peak", "Когда лучше соображаешь?", ["Утром", "Днём", "Вечером", "Ночью"]),
    (
        "blocker",
        "Что чаще всего мешает?",
        ["Откладываю на потом", "Не могу сосредоточиться", "Не знаю, с чего начать", "Быстро устаю"],
    ),
    (
        "help",
        "С чем помогать в первую очередь?",
        ["Разбирать темы", "Решать задачи", "Писать рефераты и тексты", "Код", "Готовиться к экзаменам"],
    ),
    (
        "tone",
        "Последний вопрос. Как со мной общаться?",
        ["На «ты», по-дружески", "Спокойно и по делу", "С юмором", "Строго, без поблажек"],
    ),
]

LABELS = {
    "name": "Имя",
    "level": "Где учится",
    "field": "Что изучает",
    "hard": "Сложные предметы",
    "urgent": "Срочное",
    "style": "Как лучше понимает",
    "depth": "Подробность",
    "time": "Время в день",
    "peak": "Лучшее время",
    "blocker": "Что мешает",
    "help": "Чем помогать",
    "tone": "Тон общения",
}

# ----------------------------------------------------------- режимы чата ---

MODES = {
    "📖 Объяснить": "Объясни тему: сначала суть в двух-трёх предложениях, потом разбор по шагам.",
    "🧒 Простыми словами": "Объясняй максимально просто, как человеку, который видит тему впервые. Используй бытовые аналогии.",
    "🧩 С примером": "Покажи тему на конкретных примерах, с решением и пояснением каждого шага.",
    "📝 Конспект": "Сделай короткий конспект: ключевые понятия, формулы или правила, что запомнить.",
    "✅ Проверь меня": "Не объясняй сразу. Задай мне 3 вопроса по теме по одному, дождись ответа, затем скажи, где я ошибся и почему.",
    "🗓 План": "Составь план изучения темы с разбивкой по дням и с учётом моего свободного времени.",
}

FOLLOWUPS = [
    ("Объясни проще", "Объясни то же самое проще, на бытовом примере."),
    ("Ещё пример", "Приведи ещё один пример, другой по типу."),
    ("Глубже", "Разбери подробнее, с нюансами и типичными ошибками."),
    ("Проверь меня", "Проверь меня по этой теме: задай один вопрос и дождись ответа."),
]


# ------------------------------------------------------------------- состояние ---

def init_state():
    ss = st.session_state
    ss.setdefault("stage", "setup")  # setup -> survey -> chat
    ss.setdefault("q", 0)
    ss.setdefault("profile", {})
    ss.setdefault("survey_log", [])  # [(role, text)]
    ss.setdefault("chat", [])  # [{"role", "content"}]
    ss.setdefault("pending", False)
    ss.setdefault("error", None)
    ss.setdefault("cfg", {"provider": "OpenRouter", "model": PROVIDERS["OpenRouter"]["models"][0],
                          "base_url": "", "keys": {}, "temperature": 0.6})


def secret_key(provider: str) -> str:
    name = PROVIDERS[provider]["env"]
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.environ.get(name, "")


def current_api():
    cfg = st.session_state.cfg
    p = cfg["provider"]
    base = cfg["base_url"] if p == "Свой API" else PROVIDERS[p]["base_url"]
    key = cfg["keys"].get(p) or secret_key(p)
    return base, key, cfg["model"], cfg["temperature"]


# ---------------------------------------------------------- настройки API ---

def on_provider_change():
    ss = st.session_state
    p = ss["w_provider"]
    ss.cfg["provider"] = p
    models = PROVIDERS[p]["models"]
    ss["w_model"] = models[0] if models else ""
    ss["w_key"] = ss.cfg["keys"].get(p) or secret_key(p)


def set_model(name: str):
    st.session_state["w_model"] = name


def api_settings():
    """Одни и те же поля в начале (setup) и в сайдбаре (потом)."""
    ss = st.session_state
    cfg = ss.cfg
    # Виджет переезжает из центра в сайдбар, поэтому при смене места
    # заново подставляем значения из cfg.
    loc = "side" if ss.stage == "chat" else "main"
    if ss.get("_api_loc") != loc:
        ss["w_provider"] = cfg["provider"]
        ss["w_model"] = cfg["model"]
        ss["w_base"] = cfg["base_url"]
        ss["w_key"] = cfg["keys"].get(cfg["provider"]) or secret_key(cfg["provider"])
        ss["w_temp"] = cfg["temperature"]
        ss["_api_loc"] = loc

    st.selectbox("Провайдер", list(PROVIDERS), key="w_provider", on_change=on_provider_change)
    provider = ss["w_provider"]
    info = PROVIDERS[provider]

    if provider == "Свой API":
        st.text_input("Base URL", key="w_base", placeholder="https://my-server.com/v1",
                      help="Любой сервер с OpenAI-совместимым /chat/completions")
    st.text_input("Модель", key="w_model", placeholder="например, gpt-4o-mini")
    if info["models"]:
        cols = st.columns(min(len(info["models"]), 2))
        for i, m in enumerate(info["models"]):
            cols[i % len(cols)].button(m, key=f"sug_{provider}_{i}", on_click=set_model, args=(m,),
                                       use_container_width=True)
    st.text_input("API-ключ", key="w_key", type="password",
                  help="Хранится только в памяти этой сессии и никуда не сохраняется.")
    if info["keys_url"]:
        st.caption(f"Взять ключ: {info['keys_url']}")
    st.slider("Температура", 0.0, 1.5, key="w_temp", help="Ниже — точнее, выше — свободнее.")

    cfg["provider"] = provider
    cfg["model"] = ss["w_model"].strip()
    cfg["base_url"] = ss["w_base"].strip()
    cfg["keys"][provider] = ss["w_key"].strip()
    cfg["temperature"] = ss["w_temp"]


# ------------------------------------------------------------------ экраны ---

def screen_setup():
    st.title("🎓 Помощник студента")
    st.write(
        "Чат-помощник, который объясняет темы так, как удобно именно тебе. "
        "Сначала выбери, на чём он будет работать, потом ответь на 12 коротких вопросов."
    )
    with st.expander("Из чего это сделано"):
        st.markdown(
            "- **Streamlit** — интерфейс и чат\n"
            "- **requests** — запросы к API со стримингом ответа\n"
            "- **OpenRouter, OpenAI, Groq, DeepSeek, Gemini, Mistral, Together** "
            "или любой свой сервер с OpenAI-совместимым API"
        )
    st.subheader("Шаг 1. Модель и ключ")
    api_settings()
    base, key, model, _ = current_api()
    ready = bool(base and model and key)
    if not ready:
        st.info("Нужны провайдер, модель и ключ. Без ключа дальше не пустит.")
    if st.button("Дальше — вопросы", type="primary", disabled=not ready):
        st.session_state.stage = "survey"
        st.rerun()


def answer_survey(text: str):
    ss = st.session_state
    key, question, _ = QUESTIONS[ss.q]
    ss.survey_log.append(("assistant", question))
    ss.survey_log.append(("user", text))
    ss.profile[key] = text
    ss.q += 1
    if ss.q >= len(QUESTIONS):
        ss.stage = "chat"
        ss.chat.append({"role": "assistant", "content": welcome_text()})


def welcome_text() -> str:
    p = st.session_state.profile
    parts = [f"Готово{', ' + p['name'] if p.get('name') else ''}."]
    if p.get("level") or p.get("field"):
        parts.append(f"Запомнил: {(p.get('level') or '').lower()} {p.get('field') or ''}".strip() + ".")
    if p.get("hard"):
        parts.append(f"Сложнее всего идёт: {p['hard']}.")
    if p.get("urgent") and p["urgent"] != QUESTIONS[4][2][0]:
        parts.append(f"Срочное: {p['urgent']}.")
    parts.append(
        "Напиши тему или вставь задание, а режим внизу подскажет, как с этим работать: "
        "объяснить, дать пример, сделать конспект или проверить тебя."
    )
    return " ".join(parts)


def screen_survey():
    ss = st.session_state
    st.title("🎓 Помощник студента")
    st.progress(ss.q / len(QUESTIONS), text=f"Вопрос {ss.q + 1} из {len(QUESTIONS)}")

    for role, text in ss.survey_log:
        with st.chat_message(role):
            st.write(text)

    key, question, options = QUESTIONS[ss.q]
    with st.chat_message("assistant"):
        st.write(question)
        if options:
            cols = st.columns(2)
            for i, opt in enumerate(options):
                cols[i % 2].button(opt, key=f"opt_{ss.q}_{i}", on_click=answer_survey, args=(opt,),
                                   use_container_width=True)
        st.button("Пропустить", key=f"skip_{ss.q}", type="tertiary", on_click=answer_survey, args=("",))

    text = st.chat_input("Напиши ответ или выбери вариант выше")
    if text:
        answer_survey(text.strip())
        st.rerun()


def system_prompt(mode: str) -> str:
    p = {k: v for k, v in st.session_state.profile.items() if v}
    lines = "\n".join(f"- {LABELS[k]}: {v}" for k, v in p.items())
    return (
        "Ты — личный помощник студента. Отвечай на русском, если не попросили иначе. "
        "Объясняй так, чтобы понял одногруппник, у которого не получается: просто, без жаргона, термины расшифровывай. "
        "Не выдумывай факты: если не уверен, так и скажи. Не пиши лишних вступлений.\n\n"
        f"Что известно о студенте:\n{lines}\n\n"
        "Подстраивай тон, подробность и формат под эти ответы.\n\n"
        f"Режим сейчас: {mode}\n{MODES[mode]}"
    )


def queue_user_message(text: str):
    ss = st.session_state
    ss.chat.append({"role": "user", "content": text})
    ss.pending = True
    ss.error = None


def reset_all():
    for k in list(st.session_state.keys()):
        del st.session_state[k]


def sidebar_chat():
    ss = st.session_state
    with st.sidebar:
        st.header("Профиль")
        for k, v in ss.profile.items():
            if v:
                st.markdown(f"**{LABELS[k]}:** {v}")
        st.divider()
        with st.expander("Модель и ключ"):
            api_settings()
        if st.button("Очистить чат", use_container_width=True):
            ss.chat = ss.chat[:1]
            ss.pending = False
            ss.error = None
            st.rerun()
        st.button("Пройти вопросы заново", use_container_width=True, on_click=reset_all)


def screen_chat():
    ss = st.session_state
    sidebar_chat()
    st.title("🎓 Помощник студента")

    mode = st.segmented_control("Что сделать с темой", list(MODES), default=list(MODES)[0],
                                key="mode", label_visibility="collapsed")
    mode = mode or list(MODES)[0]

    for m in ss.chat:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # Ответ модели
    if ss.pending:
        base, key, model, temp = current_api()
        history = [{"role": "system", "content": system_prompt(mode)}] + [
            {"role": m["role"], "content": m["content"]} for m in ss.chat[-20:]
        ]
        ss.pending = False
        with st.chat_message("assistant"):
            try:
                reply = st.write_stream(stream_chat(base, key, model, history, temp))
                ss.chat.append({"role": "assistant", "content": reply})
                st.rerun()
            except LLMError as e:
                ss.error = str(e)

    if ss.error:
        st.error(ss.error)
        if st.button("Повторить"):
            ss.pending = True
            ss.error = None
            st.rerun()

    # Быстрые действия после ответа
    if ss.chat and ss.chat[-1]["role"] == "assistant" and len(ss.chat) > 1:
        cols = st.columns(len(FOLLOWUPS))
        for col, (label, prompt) in zip(cols, FOLLOWUPS):
            col.button(label, key=f"fu_{len(ss.chat)}_{label}", on_click=queue_user_message,
                       args=(prompt,), use_container_width=True)

    text = st.chat_input(f"Тема или задание. Режим: {mode}")
    if text:
        queue_user_message(text)
        st.rerun()


init_state()
{"setup": screen_setup, "survey": screen_survey, "chat": screen_chat}[st.session_state.stage]()
