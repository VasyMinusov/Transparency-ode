"""Терминальный клиент (TUI) к системе «Код прозрачности».

Работает поверх запущенного сервера данных — без графического окна,
удобно на сервере или по SSH. Только стандартная библиотека Python.

Запуск:  python tools/tui_client.py
Команды: проверить <название или ИНН> · сеть · сигналы · законы · модель · выход
"""
import json
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"


def get(path: str):
    with urllib.request.urlopen(f"{BASE}{path}", timeout=60) as r:
        return json.load(r)


def post(path: str, payload: dict):
    req = urllib.request.Request(
        f"{BASE}{path}", data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def level_ru(level: str) -> str:
    return {"critical": "ТРЕБУЕТ НЕМЕДЛЕННОЙ ПРОВЕРКИ", "attention": "ПОВЫШЕННОЕ ВНИМАНИЕ",
            "normal": "В НОРМЕ", "high": "высокая степень", "medium": "средняя степень",
            "none": "в норме"}.get(level, level)


def cmd_check(query: str) -> None:
    entities = get(f"/entities?q={urllib.request.quote(query)}")
    if not entities:
        print("Ничего не найдено. Попробуйте другое название или ИНН.")
        return
    for e in entities[:3]:
        _print_entity(e)


def _print_entity(e: dict) -> None:
    print(f"\n{'=' * 66}")
    print(f"{e['name']}  ({e.get('external_id') or 'ИНН отсутствует'})")
    print(f"{'=' * 66}")
    v = get(f"/entities/{e['id']}/verdict")
    print(f"Вердикт: {level_ru(v['level'])} — {v['summary']}")
    print(f"Рекомендация: {v['recommendation']}")
    print("\nФакты:")
    for fct in v["facts"]:
        print(f"  · {fct['name']}: {fct['value']}")
    if v["signals"]:
        print("\nСигналы:")
        for s in v["signals"]:
            print(f"  ! [{level_ru(s['severity'])}] {s['scheme']} (правило {s['rule']})")
            print(f"    {s['description']}")
            print(f"    Основания: {', '.join(s['law_refs'])}")
            if s.get("action"):
                print(f"    Что запросить: {s['action']}")
    else:
        print("\nСигналов не выявлено.")
    decisions = get(f"/decisions?entity_id={e['id']}")
    if decisions:
        d = decisions[0]
        print(f"\nРешение сотрудника: {level_ru(d['decision']) if d['decision'] in ('high','medium','none') else ('подтверждён' if d['decision'] == 'confirmed' else 'отклонён')}"
              f" от {d['created_at'][:19].replace('T', ' ')}{' — ' + d['comment'] if d['comment'] else ''}")
    try:
        a = get(f"/entities/{e['id']}/agent-report")
        print(f"\nВосходящий агент ({a['provider']}):")
        print(f"  {a['narrative']}")
    except Exception as exc:
        print(f"\nАгент недоступен: {exc}")
    r = get(f"/entities/{e['id']}/report")
    if r["counterparties"]:
        print("\nСвязанные сущности (по убыванию риска):")
        for c in r["counterparties"][:7]:
            print(f"  · {c['entity']['name']}: риск {c['risk_score']:.2f} "
                  f"({level_ru(c['risk_level'])}), {c['relation_count']} контр., "
                  f"{c['total_amount']:,.0f} ₽".replace(",", " "))


def cmd_network() -> None:
    o = get("/agent/overview")
    print(f"\n=== Сеть: {o['entities_count']} сущностей, {o['relations_count']} связей ===")
    print(o["narrative"])
    for f in o["findings"]:
        print(f"  · [{f['type'].replace('_', ' ')}] {f['description']}")


def cmd_signals() -> None:
    feed = get("/signals")
    decisions = get("/decisions")
    rejected = {d["entity_id"] for d in decisions if d["decision"] == "rejected"}
    print(f"\n=== Сигналы: {len(feed)} (отклонены сотрудником: {len(rejected)} сущностей) ===")
    for s in feed:
        mark = " [ОТКЛОНЁН СОТРУДНИКОМ]" if s["entity_id"] in rejected else ""
        print(f"! [{level_ru(s['severity'])}] {s['entity_name']} — {s['scheme']}{mark}")
        print(f"  {s['description']} (основания: {', '.join(s['law_refs'])})")


def cmd_laws() -> None:
    laws = get("/laws")
    print(f"\n=== Нормативная база: {len(laws)} актов ===")
    for l in laws:
        print(f"· {l['title']}\n  {l['annotation']}")


def cmd_model(arg: str) -> None:
    if not arg:
        cur = get("/settings/llm")
        print(f"\nТекущая модель: провайдер={cur['provider']}, ollama={cur['ollama_model']} ({cur['ollama_url']})")
        print("GigaChat настроен: " + ("да" if cur["gigachat_configured"] else "нет (нужны credentials)"))
        try:
            models = get("/settings/llm/models")
            print("Локальные модели Ollama: " + (", ".join(models["models"]) or "нет"))
        except Exception:
            print("Ollama не запущен — локальные модели недоступны (ollama serve).")
        print("\nСменить: модель <offline|gigachat|ollama> [название_модели]")
        return
    parts = arg.split()
    provider = parts[0]
    if provider not in ("offline", "gigachat", "ollama"):
        print("Провайдер: offline | gigachat | ollama")
        return
    cur = get("/settings/llm")
    payload = {"provider": provider, "ollama_url": cur["ollama_url"],
               "ollama_model": parts[1] if len(parts) > 1 else cur["ollama_model"]}
    post("/settings/llm", payload)
    print(f"Установлено: {payload['provider']}"
          + (f", модель {payload['ollama_model']}" if provider == "ollama" else ""))


HELP = """Команды:
  проверить <название или ИНН> — отчёт, вердикт, агент по сущности (до 3 совпадений)
  сеть    — сводка агента по всей сети (кластеры, узлы)
  сигналы — лента сигналов (отклонённые сохраняются с пометкой)
  законы  — нормативная база
  модель  — показать текущую LLM и список локальных моделей
  модель <offline|gigachat|ollama> [модель] — сменить модель озвучивания агента
  выход   — завершить
"""


def main() -> None:
    print("Код прозрачности — терминальный клиент. Введите «помощь» для списка команд.")
    while True:
        try:
            cmd = input("кп> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания.")
            return
        if not cmd:
            continue
        verb, _, arg = cmd.partition(" ")
        if verb in ("выход", "quit", "exit"):
            print("До свидания.")
            return
        if verb in ("помощь", "help"):
            print(HELP)
        elif verb == "проверить" and arg:
            try:
                cmd_check(arg)
            except Exception as exc:
                print(f"Ошибка запроса: {exc} (сервер запущен? uvicorn на :8000)")
        elif verb == "сеть":
            cmd_network()
        elif verb == "сигналы":
            cmd_signals()
        elif verb == "законы":
            cmd_laws()
        elif verb == "модель":
            try:
                cmd_model(arg)
            except Exception as exc:
                print(f"Ошибка: {exc}")
        else:
            print("Не понял команду. Введите «помощь».")


if __name__ == "__main__":
    main()
