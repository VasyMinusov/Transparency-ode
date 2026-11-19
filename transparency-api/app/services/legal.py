"""Поиск по корпусу НПА на уровне статей (legal RAG, MVP-слой).

Best practice для юридических текстов: индекс строится по статьям (не фиксированные
чанки), запрос формируется из сущности нарушения, результат — конкретная статья
с оценкой релевантности. Провайдер поиска — TF-IDF + косинусная близость
(scikit-learn): полностью детерминирован, не требует скачивания моделей.
Интерфейс search_articles() позволяет заменить ядро на эмбеддинги
(sbert_large_nlu_ru / GigaChat Embeddings) без изменения вызывающего кода.

Корпус (data/legal_corpus.json): конспекты статей с точными номерами и названиями.
Для промышленного контура замените текст на полные редакции
(официальный источник: publication.pravo.gov.ru).
"""
import json
import re
from functools import lru_cache
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_STOP = ("и в во не что он на я с со как а то все она так его но да ты к у же вы за бы "
         "по только ее мне было вот от меня еще нет о из ему теперь когда даже ну вдруг "
         "ли если уже или ни быть был него до вас нибудь опять уж вам ведь там потом себя "
         "ничего ей может они тут где есть надо ней для мы тебя их чем была сам чтоб без "
         "будто чего раз тоже себе под будет ж тогда кто этот того потому этого какой "
         "совсем ним здесь этом один почти мой тем чтобы нее сейчас были куда зачем всех "
         "никогда можно при наконец два об другой хоть после над больше тот через эти нас "
         "про всего них какая много разве три эту моя впрочем хорошо свою этой перед "
         "иногда лучше чуть том нельзя такой им более всегда конечно всю между").split()


def _corpus_path() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "data" / "legal_corpus.json"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("data/legal_corpus.json не найден")


@lru_cache(maxsize=1)
def _index():
    corpus = json.loads(_corpus_path().read_text(encoding="utf-8"))
    texts = [f"{e['title']}. {e['text']}. {e['keywords']}" for e in corpus]
    vec = TfidfVectorizer(ngram_range=(1, 2), stop_words=_STOP)
    matrix = vec.fit_transform(texts)
    return corpus, vec, matrix


def search_articles(query: str, top_k: int = 5, min_score: float = 0.05) -> list[dict]:
    """Релевантные статьи по запросу. query — свободное описание нарушения."""
    corpus, vec, matrix = _index()
    q = vec.transform([query])
    scores = cosine_similarity(q, matrix)[0]
    order = sorted(range(len(corpus)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [
        {"id": corpus[i]["id"], "act": corpus[i]["act"], "act_title": corpus[i]["act_title"],
         "article": corpus[i]["article"], "title": corpus[i]["title"],
         "excerpt": corpus[i]["text"], "score": round(float(scores[i]), 4)}
        for i in order if scores[i] >= min_score
    ]


def article_by_id(article_id: str) -> dict | None:
    corpus, _, _ = _index()
    return next((e for e in corpus if e["id"] == article_id), None)


def acts_summary() -> list[dict]:
    corpus, _, _ = _index()
    out: dict[str, dict] = {}
    for e in corpus:
        a = out.setdefault(e["act"], {"act": e["act"], "act_title": e["act_title"], "articles": 0})
        a["articles"] += 1
    return list(out.values())


_TOKEN_RE = re.compile(r"[a-zа-яё0-9]+", re.IGNORECASE)


def query_from_signal(scheme: str, description: str, facts: dict) -> str:
    """Запрос в корпус из сигнала: схема + текст + факты (ключи и значения)."""
    parts = [scheme, description, " ".join(str(v) for v in facts.values())]
    return " ".join(parts)
