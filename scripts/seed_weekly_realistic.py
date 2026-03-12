from __future__ import annotations

import argparse
import json
import random
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from uuid import uuid4

MSK_OFFSET = timedelta(hours=3)
SYNTHETIC_PREFIX = "synthetic_weekly_"

FIRST_NAMES = [
    "Алексей",
    "Марина",
    "Дмитрий",
    "Елена",
    "Ирина",
    "Максим",
    "Ольга",
    "Сергей",
    "Анна",
    "Наталья",
    "Илья",
    "Виктория",
]

LAST_NAMES = [
    "Иванов",
    "Петрова",
    "Смирнов",
    "Кузнецова",
    "Васильев",
    "Соколова",
    "Морозов",
    "Попова",
    "Орлова",
    "Козлова",
]

INDUSTRIES = [
    "стоматология",
    "онлайн-образование",
    "недвижимость",
    "косметология",
    "юридические услуги",
    "фитнес",
    "ремонт квартир",
    "автосервис",
    "медицинский центр",
    "маркетинговое агентство",
]

SERVICES = [
    "AI Sales Audit",
    "CRM Integration",
    "Conversation Design",
    "Analytics Setup",
    "LLM Prompt Tuning",
]

SLOTS = [
    "завтра в 11:00",
    "завтра в 15:00",
    "в четверг в 12:30",
    "в пятницу в 16:00",
    "в понедельник в 10:00",
]


@dataclass(frozen=True)
class TurnTemplate:
    user_variants: tuple[str, ...]
    bot_variants: tuple[str, ...]
    intent: str
    assistant_action: str = "reply"
    confidence_delta: float = 0.0


@dataclass(frozen=True)
class ScenarioTemplate:
    key: str
    stage: str
    last_intent: str
    handoff_requested: bool
    is_booked: bool
    confidence_min: float
    confidence_max: float
    turns: tuple[TurnTemplate, ...]


SCENARIOS: tuple[ScenarioTemplate, ...] = (
    ScenarioTemplate(
        key="quick_booking",
        stage="booked",
        last_intent="booking_intent",
        handoff_requested=False,
        is_booked=True,
        confidence_min=0.82,
        confidence_max=0.98,
        turns=(
            TurnTemplate(
                user_variants=(
                    "Здравствуйте! У нас {industry}, хочу понять, как ускорить обработку заявок.",
                    "Добрый день, интересует внедрение AI-бота в {industry}.",
                ),
                bot_variants=(
                    "Отлично, расскажу. Сколько заявок в день обрабатываете сейчас?",
                    "Хороший запрос. Подскажите, на каком этапе чаще теряете клиентов?",
                ),
                intent="service_question",
            ),
            TurnTemplate(
                user_variants=(
                    "Около 35 обращений в день, особенно проседает скорость первого ответа.",
                    "Сейчас 20-30 обращений, менеджеры не успевают отвечать вовремя.",
                ),
                bot_variants=(
                    "Понял, для такого объема подходит пакет {service}. Стоимость от 35 000 ₽.",
                    "Рекомендую начать с {service}. Обычно окупается за 1-2 месяца.",
                ),
                intent="price_question",
            ),
            TurnTemplate(
                user_variants=(
                    "Ок, подходит. Можно созвониться {slot}?",
                    "Давайте созвон, мне удобно {slot}.",
                ),
                bot_variants=(
                    "Отлично, подтверждаю консультацию {slot}.",
                    "Зафиксировал встречу {slot}. Перед консультацией пришлю короткий бриф.",
                ),
                intent="booking_intent",
            ),
        ),
    ),
    ScenarioTemplate(
        key="price_objection",
        stage="lost",
        last_intent="objection",
        handoff_requested=False,
        is_booked=False,
        confidence_min=0.63,
        confidence_max=0.9,
        turns=(
            TurnTemplate(
                user_variants=(
                    "Смотрю решение для {industry}, но бюджет ограничен.",
                    "Интересует автоматизация продаж, но пока не уверен по стоимости.",
                ),
                bot_variants=(
                    "Понимаю. Расскажите ваш текущий процесс, предложу подходящий формат.",
                    "Давайте оценим задачу, чтобы подобрать минимальный стартовый пакет.",
                ),
                intent="service_question",
            ),
            TurnTemplate(
                user_variants=(
                    "Если честно, 35 тысяч в месяц для нас дорого.",
                    "Пока получается выше нашего бюджета.",
                ),
                bot_variants=(
                    "Можем запустить пилот: меньше функций, но быстрый эффект за 2 недели.",
                    "Есть мягкий старт с ограниченным контуром. Хотите смету на пилот?",
                ),
                intent="objection",
            ),
            TurnTemplate(
                user_variants=(
                    "Давайте пока отложим, вернусь позже.",
                    "Сейчас не готовы, возможно через месяц.",
                ),
                bot_variants=(
                    "Принято, сохраню контакт и вернусь с предложением через пару недель.",
                    "Хорошо, напомню позже и пришлю кейсы по вашему сегменту.",
                ),
                intent="objection",
                confidence_delta=-0.05,
            ),
        ),
    ),
    ScenarioTemplate(
        key="handoff_enterprise",
        stage="qualified",
        last_intent="service_question",
        handoff_requested=True,
        is_booked=False,
        confidence_min=0.72,
        confidence_max=0.96,
        turns=(
            TurnTemplate(
                user_variants=(
                    "У нас сеть из 12 филиалов, нужен нестандартный сценарий и интеграция с 1С.",
                    "Кейс сложный, хочу сразу обсудить с менеджером внедрения.",
                ),
                bot_variants=(
                    "Да, для такого кейса подключим специалиста по интеграциям.",
                    "Понял задачу, передаю запрос менеджеру проекта.",
                ),
                intent="service_question",
            ),
            TurnTemplate(
                user_variants=(
                    "Да, прошу передать. Нужен контакт сегодня до 18:00.",
                    "Ок, соедините с менеджером, пожалуйста.",
                ),
                bot_variants=(
                    "Передал менеджеру. Свяжется с вами сегодня до 18:00.",
                    "Сделано, менеджер уже получил ваш запрос.",
                ),
                intent="service_question",
                assistant_action="handoff",
            ),
        ),
    ),
    ScenarioTemplate(
        key="warm_interest",
        stage="interested",
        last_intent="service_question",
        handoff_requested=False,
        is_booked=False,
        confidence_min=0.71,
        confidence_max=0.94,
        turns=(
            TurnTemplate(
                user_variants=(
                    "Какие услуги вы даете для {industry}?",
                    "Есть решение под {industry} с Telegram и CRM?",
                ),
                bot_variants=(
                    "Да, обычно начинаем с {service}, затем подключаем аналитику и авто-воронку.",
                    "Есть. Можем собрать воронку под ваш цикл сделки за 2-3 недели.",
                ),
                intent="service_question",
            ),
            TurnTemplate(
                user_variants=(
                    "Понял, пришлите пример проекта и примерные сроки.",
                    "Интересно, дайте кейс и ориентир по этапам.",
                ),
                bot_variants=(
                    "Отправлю 2 кейса и план этапов: аудит -> сценарии -> запуск -> оптимизация.",
                    "Сейчас пришлю короткий план внедрения и ориентиры по срокам.",
                ),
                intent="service_question",
            ),
            TurnTemplate(
                user_variants=(
                    "Хорошо, изучу и вернусь с решением завтра.",
                    "Спасибо, посмотрю материалы и отпишусь завтра.",
                ),
                bot_variants=(
                    "Отлично, буду на связи. Могу завтра предложить 2 слота на консультацию.",
                    "Договорились. Если удобно, завтра напомню и предложу время созвона.",
                ),
                intent="booking_intent",
            ),
        ),
    ),
    ScenarioTemplate(
        key="contact_exchange",
        stage="booking_pending",
        last_intent="contact_sharing",
        handoff_requested=False,
        is_booked=False,
        confidence_min=0.74,
        confidence_max=0.95,
        turns=(
            TurnTemplate(
                user_variants=(
                    "Интересно, можем продолжить в WhatsApp?",
                    "Могу оставить номер и обсудить подробнее по телефону.",
                ),
                bot_variants=(
                    "Да, конечно. Оставьте номер, менеджер свяжется и согласует время.",
                    "Отлично, оставьте контакт и удобное окно для звонка.",
                ),
                intent="contact_sharing",
            ),
            TurnTemplate(
                user_variants=(
                    "Запишите: +7 999 456-32-11, лучше после 16:00.",
                    "Мой номер +7 925 111-22-33, удобно после обеда.",
                ),
                bot_variants=(
                    "Принял контакт, передаю менеджеру. Подтвердим время сегодня.",
                    "Контакт получил, менеджер свяжется в указанное время.",
                ),
                intent="contact_sharing",
            ),
        ),
    ),
    ScenarioTemplate(
        key="unclear_path",
        stage="engaged",
        last_intent="unclear",
        handoff_requested=False,
        is_booked=False,
        confidence_min=0.22,
        confidence_max=0.58,
        turns=(
            TurnTemplate(
                user_variants=(
                    "Не понимаю, а вы вообще что делаете?",
                    "Мне сложно объяснить, что именно нужно.",
                ),
                bot_variants=(
                    "Давайте проще: мы помогаем быстрее отвечать лидам и повышать записи.",
                    "Могу уточнить в 2 вопроса и предложить подходящий сценарий.",
                ),
                intent="unclear",
                confidence_delta=-0.12,
            ),
            TurnTemplate(
                user_variants=(
                    "Наверное, мне нужно чтобы клиентов не теряли менеджеры.",
                    "Хочу, чтобы бот не давал лидам пропадать после первого сообщения.",
                ),
                bot_variants=(
                    "Отлично, это решаемо: автоответ + follow-up + контроль воронки.",
                    "Понял задачу. Предлагаю короткий аудит, чтобы показать точки потерь.",
                ),
                intent="service_question",
                confidence_delta=-0.05,
            ),
            TurnTemplate(
                user_variants=(
                    "Хорошо, подумаю и напишу позже.",
                    "Ок, пока не готов, вернусь к теме.",
                ),
                bot_variants=(
                    "Хорошо, буду на связи. Если захотите, подготовлю персональные рекомендации.",
                    "Принято. Когда будете готовы, вернемся к обсуждению.",
                ),
                intent="unclear",
                confidence_delta=-0.15,
            ),
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate realistic weekly synthetic dialogs")
    parser.add_argument(
        "--db-path",
        default="/Users/alinasemicheva/Documents/AI инженер/AI seller Alina v2/AI Sales Analytics/data/alina_weekly_demo.db",
        help="SQLite DB path",
    )
    parser.add_argument(
        "--end-date",
        default=date.today().isoformat(),
        help="Last day of generation window (YYYY-MM-DD)",
    )
    parser.add_argument("--days", type=int, default=7, help="Number of days to generate")
    parser.add_argument("--dialogs-per-day", type=int, default=10, help="Dialogs per each day")
    parser.add_argument("--seed", type=int, default=20260312, help="Random seed")
    parser.add_argument(
        "--purge-synthetic",
        action="store_true",
        help="Delete previous synthetic leads (username starts with synthetic_) before insert",
    )
    return parser.parse_args()


def utc_str(dt_utc: datetime) -> str:
    return dt_utc.strftime("%Y-%m-%d %H:%M:%S")


def msk_to_utc(dt_msk: datetime) -> datetime:
    return dt_msk - MSK_OFFSET


def random_name() -> tuple[str, str]:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    return first, f"{first} {last}"


def ensure_services(conn: sqlite3.Connection, now_utc: datetime) -> None:
    seed_services = [
        ("AI Sales Audit", "Аудит воронки и диалогов", 12000, "RUB"),
        ("CRM Integration", "Интеграция бота с CRM", 35000, "RUB"),
        ("Conversation Design", "Проработка скриптов и возражений", 18000, "RUB"),
        ("Analytics Setup", "Настройка аналитики и ежедневных отчетов", 22000, "RUB"),
        ("LLM Prompt Tuning", "Оптимизация intent/stage классификации", 15000, "RUB"),
    ]
    for name, description, price_from, currency in seed_services:
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
    lead_ids = [
        row[0]
        for row in conn.execute(
            "SELECT id FROM leads WHERE username LIKE 'synthetic_%' OR username LIKE 'demo_%'"
        ).fetchall()
    ]
    if not lead_ids:
        return (0, 0, 0)

    placeholders = ",".join(["?"] * len(lead_ids))
    ai_deleted = conn.execute(f"DELETE FROM ai_runs WHERE lead_id IN ({placeholders})", lead_ids).rowcount
    msg_deleted = conn.execute(f"DELETE FROM messages WHERE lead_id IN ({placeholders})", lead_ids).rowcount
    lead_deleted = conn.execute(f"DELETE FROM leads WHERE id IN ({placeholders})", lead_ids).rowcount
    return (lead_deleted, msg_deleted, ai_deleted)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def random_day_time(day: date, index: int) -> datetime:
    base_hour = 9 + (index % 10)
    minute = random.randint(0, 55)
    return datetime.combine(day, time(hour=base_hour, minute=minute))


def build_context() -> dict[str, str]:
    industry = random.choice(INDUSTRIES)
    service = random.choice(SERVICES)
    slot = random.choice(SLOTS)
    budget = random.choice(["до 30 000", "40-60 000", "80 000+"])
    return {
        "industry": industry,
        "service": service,
        "slot": slot,
        "budget": budget,
    }


def insert_lead(
    conn: sqlite3.Connection,
    *,
    lead_id: str,
    telegram_user_id: int,
    username: str,
    full_name: str,
    created_utc: datetime,
    scenario: ScenarioTemplate,
    context: dict[str, str],
) -> None:
    booking_slot_at = None
    if scenario.is_booked:
        booking_slot_at = created_utc + timedelta(hours=random.randint(2, 18))

    if scenario.stage in {"booked", "lost"}:
        next_follow_up_at = None
        follow_up_step = 0
    else:
        next_follow_up_at = created_utc + timedelta(hours=random.randint(10, 36))
        follow_up_step = random.choice([0, 1])

    qualification_data = {
        "source": "weekly_realistic_seed",
        "scenario": scenario.key,
        "industry": context["industry"],
        "budget_band": context["budget"],
        "pain_points": random.sample(
            [
                "долго отвечают менеджеры",
                "нет прозрачной воронки",
                "лиды пропадают после первого контакта",
                "сложно контролировать follow-up",
                "нет единой аналитики по диалогам",
            ],
            k=2,
        ),
    }

    conn.execute(
        """
        INSERT INTO leads (
            id, telegram_user_id, telegram_chat_id, username, full_name,
            phone, email, stage, last_intent, created_at, updated_at,
            qualification_data, follow_up_step, next_follow_up_at,
            do_not_contact, stopped_at, last_user_message_at,
            last_bot_message_at, booking_slot_at, handoff_requested
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            lead_id,
            telegram_user_id,
            telegram_user_id,
            username,
            full_name,
            f"+7 9{telegram_user_id % 1000000000:09d}",
            f"{username}@example.com",
            scenario.stage,
            scenario.last_intent,
            utc_str(created_utc),
            utc_str(created_utc),
            json.dumps(qualification_data, ensure_ascii=False),
            follow_up_step,
            utc_str(next_follow_up_at) if next_follow_up_at else None,
            0,
            None,
            utc_str(created_utc + timedelta(minutes=3)),
            utc_str(created_utc + timedelta(minutes=5)),
            utc_str(booking_slot_at) if booking_slot_at else None,
            1 if scenario.handoff_requested else 0,
        ),
    )


def insert_dialog(
    conn: sqlite3.Connection,
    *,
    lead_id: str,
    telegram_user_id: int,
    start_utc: datetime,
    scenario: ScenarioTemplate,
    context: dict[str, str],
) -> tuple[int, int, datetime, datetime]:
    msg_count = 0
    run_count = 0
    last_user_dt = start_utc
    last_bot_dt = start_utc
    current = start_utc

    for turn_idx, turn in enumerate(scenario.turns, start=1):
        incoming_id = str(uuid4())
        outgoing_id = str(uuid4())

        user_dt = current + timedelta(minutes=random.randint(1, 8))
        bot_dt = user_dt + timedelta(minutes=random.randint(1, 4))

        user_text = random.choice(turn.user_variants).format(**context)
        bot_text = random.choice(turn.bot_variants).format(**context)

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
                user_text,
                1000000 + telegram_user_id * 10 + turn_idx,
                2000000 + telegram_user_id * 10 + turn_idx,
                utc_str(user_dt),
                utc_str(user_dt),
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
                bot_text,
                3000000 + telegram_user_id * 10 + turn_idx,
                utc_str(bot_dt),
                utc_str(bot_dt),
            ),
        )

        confidence = clamp(
            random.uniform(scenario.confidence_min, scenario.confidence_max) + turn.confidence_delta,
            0.05,
            0.99,
        )
        raw_response = {
            "provider": "weekly_realistic_seed",
            "scenario": scenario.key,
            "assistant_action": turn.assistant_action,
            "handoff_to_admin": turn.assistant_action == "handoff",
            "industry": context["industry"],
            "service": context["service"],
        }

        conn.execute(
            """
            INSERT INTO ai_runs (
                id, lead_id, input_message_id, model, prompt_version,
                intent, predicted_stage, confidence, reply_text,
                raw_response, latency_ms, status, error_text, created_at, updated_at
            ) VALUES (?, ?, ?, 'gpt-4.1-mini', 'v1', ?, ?, ?, ?, ?, ?, 'success', NULL, ?, ?)
            """,
            (
                str(uuid4()),
                lead_id,
                incoming_id,
                turn.intent,
                scenario.stage,
                round(confidence, 2),
                bot_text,
                json.dumps(raw_response, ensure_ascii=False),
                random.randint(700, 2400),
                utc_str(bot_dt),
                utc_str(bot_dt),
            ),
        )

        current = bot_dt
        last_user_dt = user_dt
        last_bot_dt = bot_dt
        msg_count += 2
        run_count += 1

    return msg_count, run_count, last_user_dt, last_bot_dt


def update_lead_message_timestamps(
    conn: sqlite3.Connection,
    *,
    lead_id: str,
    last_user_dt: datetime,
    last_bot_dt: datetime,
) -> None:
    conn.execute(
        "UPDATE leads SET last_user_message_at = ?, last_bot_message_at = ?, updated_at = ? WHERE id = ?",
        (utc_str(last_user_dt), utc_str(last_bot_dt), utc_str(last_bot_dt), lead_id),
    )


def main() -> None:
    args = parse_args()
    random.seed(args.seed)

    db_path = Path(args.db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"DB file not found: {db_path}")

    end_day = datetime.strptime(args.end_date, "%Y-%m-%d").date()
    start_day = end_day - timedelta(days=args.days - 1)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON")

        now_utc = msk_to_utc(datetime.combine(end_day, time(hour=12, minute=0)))
        ensure_services(conn, now_utc)

        deleted = (0, 0, 0)
        if args.purge_synthetic:
            deleted = purge_previous_synthetic(conn)

        inserted_leads = 0
        inserted_messages = 0
        inserted_runs = 0

        user_id_counter = 910000

        current_day = start_day
        while current_day <= end_day:
            for i in range(args.dialogs_per_day):
                scenario = random.choice(SCENARIOS)
                lead_id = str(uuid4())

                first_name, full_name = random_name()
                username = f"{SYNTHETIC_PREFIX}{current_day.strftime('%m%d')}_{i+1:02d}"

                context = build_context()
                created_msk = random_day_time(current_day, i)
                created_utc = msk_to_utc(created_msk)

                insert_lead(
                    conn,
                    lead_id=lead_id,
                    telegram_user_id=user_id_counter,
                    username=username,
                    full_name=full_name,
                    created_utc=created_utc,
                    scenario=scenario,
                    context=context,
                )

                msg_count, run_count, last_user_dt, last_bot_dt = insert_dialog(
                    conn,
                    lead_id=lead_id,
                    telegram_user_id=user_id_counter,
                    start_utc=created_utc,
                    scenario=scenario,
                    context=context,
                )
                update_lead_message_timestamps(
                    conn,
                    lead_id=lead_id,
                    last_user_dt=last_user_dt,
                    last_bot_dt=last_bot_dt,
                )

                inserted_leads += 1
                inserted_messages += msg_count
                inserted_runs += run_count
                user_id_counter += 1

            current_day += timedelta(days=1)

        conn.commit()

        print("Weekly realistic seed completed")
        print(f"DB: {db_path}")
        print(f"Window: {start_day.isoformat()} .. {end_day.isoformat()}")
        print(f"Dialogs/day: {args.dialogs_per_day}")
        print(
            "Deleted synthetic: "
            f"leads={deleted[0]}, messages={deleted[1]}, ai_runs={deleted[2]}"
        )
        print(
            f"Inserted: leads={inserted_leads}, messages={inserted_messages}, ai_runs={inserted_runs}"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
