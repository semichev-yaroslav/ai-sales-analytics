from __future__ import annotations

import argparse
import json
import random
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from itertools import zip_longest
from pathlib import Path
from uuid import uuid4

MSK_OFFSET = timedelta(hours=3)


@dataclass(frozen=True)
class Scenario:
    name: str
    stage: str
    last_intent: str
    handoff_requested: bool
    booked: bool
    lost: bool
    confidence_range: tuple[float, float]


SCENARIOS: list[Scenario] = [
    Scenario("booked_fast", "booked", "booking_intent", False, True, False, (0.82, 0.98)),
    Scenario("price_objection_lost", "lost", "objection", False, False, True, (0.62, 0.9)),
    Scenario("handoff_needed", "qualified", "service_question", True, False, False, (0.7, 0.95)),
    Scenario("unclear_dialog", "engaged", "unclear", False, False, False, (0.2, 0.55)),
    Scenario("service_interest", "interested", "service_question", False, False, False, (0.7, 0.93)),
    Scenario("booking_pending", "booking_pending", "booking_intent", False, False, False, (0.75, 0.97)),
]

USER_TEXTS = {
    "booked_fast": [
        "Здравствуйте! Нужна консультация по внедрению AI в продажи.",
        "Сколько стоит и когда можно созвониться?",
        "Да, готов записаться завтра в 14:00.",
    ],
    "price_objection_lost": [
        "Добрый день, интересуют услуги по автоматизации.",
        "Ого, для меня это дороговато.",
        "Пока отложим, вернусь позже.",
    ],
    "handoff_needed": [
        "Мне нужен нестандартный кейс, можно с менеджером?",
        "Хочу обсудить детали лично.",
        "Передайте, пожалуйста, человеку.",
    ],
    "unclear_dialog": [
        "Привет",
        "Ну это как бы не то, что я хотел",
        "Не понимаю, что дальше",
    ],
    "service_interest": [
        "Какие есть пакеты услуг для малого бизнеса?",
        "Интересует интеграция с CRM и Telegram.",
        "Есть примеры кейсов?",
    ],
    "booking_pending": [
        "Хочу консультацию, но пока не выбрал время.",
        "Давайте варианты слотов на этой неделе.",
        "Я напишу вечером и подтвержу.",
    ],
}

BOT_TEXTS = {
    "booked_fast": [
        "Отлично, помогу подобрать формат. Уточните ваш бизнес-контекст.",
        "Базовый формат от 15 000 рублей. Могу предложить удобные слоты.",
        "Зафиксировал. Подтверждаю консультацию и отправлю напоминание.",
    ],
    "price_objection_lost": [
        "Понимаю ваш вопрос. Подскажите, какой бюджет комфортен?",
        "Можем начать с пилотного формата с меньшим бюджетом.",
        "Хорошо, сохраню контакт и вернусь с оффером позже.",
    ],
    "handoff_needed": [
        "Да, подключим менеджера. Коротко опишите задачу.",
        "Передал запрос, менеджер свяжется в ближайшее время.",
        "Спасибо, менеджер уже в курсе вашего кейса.",
    ],
    "unclear_dialog": [
        "Давайте уточним: вы хотите консультацию, расчет или демо?",
        "Понял, переформулирую. Какая задача сейчас приоритетна?",
        "Если удобно, могу передать менеджеру для ручной консультации.",
    ],
    "service_interest": [
        "Есть пакеты: аудит, внедрение, сопровождение.",
        "Можем интегрировать CRM, Telegram и аналитику продаж.",
        "Да, есть кейсы по росту конверсии и сокращению ответа.",
    ],
    "booking_pending": [
        "Хорошо, подберем слот. Вам удобнее утро или вечер?",
        "Могу предложить среду 12:00 или четверг 16:00.",
        "Договорились, жду подтверждение и сразу зафиксирую слот.",
    ],
}

INTENT_BY_SCENARIO = {
    "booked_fast": "booking_intent",
    "price_objection_lost": "objection",
    "handoff_needed": "service_question",
    "unclear_dialog": "unclear",
    "service_interest": "service_question",
    "booking_pending": "booking_intent",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed synthetic dialogs for AI-Saller-Alina-v2-new SQLite DB")
    parser.add_argument(
        "--db-path",
        default="/Users/alinasemicheva/Documents/AI инженер/AI seller Alina v2/AI-Saller-Alina-v2-new/local.db",
        help="Path to local.db",
    )
    parser.add_argument("--dialogs", type=int, default=20, help="Number of synthetic dialogs to generate")
    parser.add_argument("--report-date", type=str, default=date.today().isoformat(), help="Date in YYYY-MM-DD")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    return parser.parse_args()


def utc_str(dt_utc: datetime) -> str:
    return dt_utc.strftime("%Y-%m-%d %H:%M:%S")


def msk_to_utc(dt_msk: datetime) -> datetime:
    return dt_msk - MSK_OFFSET


def ensure_services(conn: sqlite3.Connection, now_utc: datetime) -> None:
    services = [
        ("AI Sales Audit", "Аудит текущей воронки и диалогов", 12000, "RUB"),
        ("CRM Integration", "Интеграция бота с CRM и webhook-событиями", 35000, "RUB"),
        ("Conversation Design", "Проработка сценариев и objection handling", 18000, "RUB"),
        ("Analytics Setup", "Подключение аналитики и ежедневных отчетов", 22000, "RUB"),
        ("LLM Prompt Tuning", "Оптимизация intent/stage классификации", 15000, "RUB"),
    ]

    for name, description, price_from, currency in services:
        row = conn.execute("SELECT id FROM services WHERE name = ?", (name,)).fetchone()
        if row:
            continue
        conn.execute(
            """
            INSERT INTO services (
                id, name, description, price_from, currency, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (str(uuid4()), name, description, price_from, currency, utc_str(now_utc), utc_str(now_utc)),
        )


def purge_previous_synthetic(conn: sqlite3.Connection) -> tuple[int, int, int]:
    lead_ids = [row[0] for row in conn.execute("SELECT id FROM leads WHERE username LIKE 'synthetic_%'").fetchall()]
    if not lead_ids:
        return (0, 0, 0)

    placeholders = ",".join(["?"] * len(lead_ids))
    ai_deleted = conn.execute(f"DELETE FROM ai_runs WHERE lead_id IN ({placeholders})", lead_ids).rowcount
    msg_deleted = conn.execute(f"DELETE FROM messages WHERE lead_id IN ({placeholders})", lead_ids).rowcount
    lead_deleted = conn.execute(f"DELETE FROM leads WHERE id IN ({placeholders})", lead_ids).rowcount
    return (lead_deleted, msg_deleted, ai_deleted)


def insert_lead(conn: sqlite3.Connection, *, lead_id: str, user_id: int, created_at: datetime, scenario: Scenario) -> None:
    booking_slot_at = created_at + timedelta(hours=random.randint(2, 24)) if scenario.booked else None
    next_follow_up_at = created_at + timedelta(hours=random.randint(6, 20)) if not scenario.booked else None

    qualification_data = {
        "source": "synthetic_seed",
        "scenario": scenario.name,
        "priority": random.choice(["low", "medium", "high"]),
        "budget": random.choice(["unknown", "tight", "ok"]),
    }

    conn.execute(
        """
        INSERT INTO leads (
            id, telegram_user_id, telegram_chat_id, username, full_name, phone, email,
            stage, last_intent, created_at, updated_at, qualification_data,
            follow_up_step, next_follow_up_at, do_not_contact, stopped_at,
            last_user_message_at, last_bot_message_at, booking_slot_at, handoff_requested
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?, ?, ?)
        """,
        (
            lead_id,
            user_id,
            user_id,
            f"synthetic_{user_id}",
            f"Synthetic Lead {user_id}",
            f"+7999{user_id % 1000000:06d}",
            f"synthetic{user_id}@example.com",
            scenario.stage,
            scenario.last_intent,
            utc_str(created_at),
            utc_str(created_at),
            json.dumps(qualification_data, ensure_ascii=False),
            1 if next_follow_up_at else 0,
            utc_str(next_follow_up_at) if next_follow_up_at else None,
            utc_str(created_at + timedelta(hours=1)),
            utc_str(created_at + timedelta(hours=1, minutes=2)),
            utc_str(booking_slot_at) if booking_slot_at else None,
            1 if scenario.handoff_requested else 0,
        ),
    )


def insert_messages_and_ai_runs(
    conn: sqlite3.Connection,
    *,
    lead_id: str,
    created_at: datetime,
    scenario: Scenario,
    user_id: int,
) -> tuple[int, int]:
    user_msgs = USER_TEXTS[scenario.name]
    bot_msgs = BOT_TEXTS[scenario.name]
    intent = INTENT_BY_SCENARIO[scenario.name]

    msg_count = 0
    run_count = 0

    current = created_at
    sentinel = object()
    for idx, pair in enumerate(zip_longest(user_msgs, bot_msgs, fillvalue=sentinel), start=1):
        if sentinel in pair:
            raise ValueError(f"User/Bot template mismatch for scenario '{scenario.name}'")
        u_text, b_text = pair
        incoming_id = str(uuid4())
        outgoing_id = str(uuid4())

        incoming_time = current + timedelta(minutes=random.randint(1, 4))
        outgoing_time = incoming_time + timedelta(minutes=random.randint(1, 3))

        conn.execute(
            """
            INSERT INTO messages (
                id, lead_id, source, channel, text,
                telegram_message_id, telegram_update_id,
                delivery_status, delivery_error, created_at, updated_at
            ) VALUES (?, ?, 'user', ?, ?, ?, ?, 'sent', NULL, ?, ?)
            """,
            (
                incoming_id,
                lead_id,
                random.choice(["telegram", "api_simulation"]),
                u_text,
                700000 + user_id * 10 + idx,
                800000 + user_id * 10 + idx,
                utc_str(incoming_time),
                utc_str(incoming_time),
            ),
        )

        conn.execute(
            """
            INSERT INTO messages (
                id, lead_id, source, channel, text,
                telegram_message_id, telegram_update_id,
                delivery_status, delivery_error, created_at, updated_at
            ) VALUES (?, ?, 'assistant', ?, ?, ?, NULL, 'sent', NULL, ?, ?)
            """,
            (
                outgoing_id,
                lead_id,
                random.choice(["telegram", "api_simulation"]),
                b_text,
                900000 + user_id * 10 + idx,
                utc_str(outgoing_time),
                utc_str(outgoing_time),
            ),
        )

        confidence = round(random.uniform(*scenario.confidence_range), 2)
        assistant_action = "handoff" if (scenario.handoff_requested and idx >= 2) else "reply"
        predicted_stage = scenario.stage

        conn.execute(
            """
            INSERT INTO ai_runs (
                id, lead_id, input_message_id, model, prompt_version,
                intent, predicted_stage, confidence, reply_text,
                raw_response, latency_ms, status, error_text, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'success', NULL, ?, ?)
            """,
            (
                str(uuid4()),
                lead_id,
                incoming_id,
                "gpt-4.1-mini",
                "v1",
                intent,
                predicted_stage,
                confidence,
                b_text,
                json.dumps(
                    {
                        "provider": "synthetic_seed",
                        "scenario": scenario.name,
                        "assistant_action": assistant_action,
                        "handoff_to_admin": assistant_action == "handoff",
                    },
                    ensure_ascii=False,
                ),
                random.randint(700, 2400),
                utc_str(outgoing_time),
                utc_str(outgoing_time),
            ),
        )

        msg_count += 2
        run_count += 1
        current = outgoing_time

    return msg_count, run_count


def main() -> None:
    args = parse_args()
    random.seed(args.seed)

    db_path = Path(args.db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"DB file not found: {db_path}")

    report_day = datetime.strptime(args.report_date, "%Y-%m-%d").date()
    day_start_msk = datetime.combine(report_day, datetime.min.time())

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON")

        now_utc = msk_to_utc(day_start_msk + timedelta(hours=9))
        ensure_services(conn, now_utc)

        deleted_leads, deleted_messages, deleted_runs = purge_previous_synthetic(conn)

        inserted_leads = 0
        inserted_messages = 0
        inserted_runs = 0

        base_user_id = 880000

        for idx in range(args.dialogs):
            scenario = SCENARIOS[idx % len(SCENARIOS)]
            lead_id = str(uuid4())
            user_id = base_user_id + idx

            created_msk = day_start_msk + timedelta(hours=9 + (idx % 10), minutes=(idx * 7) % 60)
            created_utc = msk_to_utc(created_msk)

            insert_lead(
                conn,
                lead_id=lead_id,
                user_id=user_id,
                created_at=created_utc,
                scenario=scenario,
            )
            msg_count, run_count = insert_messages_and_ai_runs(
                conn,
                lead_id=lead_id,
                created_at=created_utc,
                scenario=scenario,
                user_id=user_id,
            )

            inserted_leads += 1
            inserted_messages += msg_count
            inserted_runs += run_count

        conn.commit()

        print("Synthetic seed completed")
        print(f"DB: {db_path}")
        print(f"Report date base: {report_day.isoformat()}")
        print(f"Deleted old synthetic: leads={deleted_leads}, messages={deleted_messages}, ai_runs={deleted_runs}")
        print(f"Inserted: leads={inserted_leads}, messages={inserted_messages}, ai_runs={inserted_runs}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
