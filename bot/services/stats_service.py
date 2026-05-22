from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import TestAttempt, User
from bot.locales import subject_name, t
from bot.services.progress_service import (
    TREND_DECLINE,
    TREND_IMPROVEMENT,
    TREND_NOT_ENOUGH_DATA,
    TREND_STABLE,
    get_progress_trend,
    get_recent_attempts,
    get_subject_performance,
    get_topic_performance,
)

async def get_user_statistics(
    session: AsyncSession,
    telegram_id: int,
    profile: dict | None = None,
) -> dict[str, object]:
    user_id_subquery = select(User.id).where(User.telegram_id == telegram_id).scalar_subquery()
    user_result = await session.execute(select(User.id).where(User.telegram_id == telegram_id))
    user_id = user_result.scalar_one_or_none()
    full_max_score = float(profile["max_score"]) if profile else 189.0

    summary_result = await session.execute(
        select(
            func.count(TestAttempt.id),
            func.avg(TestAttempt.accuracy_percent),
            func.avg(TestAttempt.score),
            func.max(TestAttempt.score),
        ).where(TestAttempt.user_id == user_id_subquery)
    )
    total_attempts, average_accuracy, average_score, best_score = summary_result.one()

    latest_result = await session.execute(
        select(TestAttempt)
        .where(TestAttempt.user_id == user_id_subquery)
        .order_by(desc(TestAttempt.finished_at))
        .limit(1)
    )
    latest_attempt = latest_result.scalar_one_or_none()

    return {
        "total_attempts": total_attempts or 0,
        "average_accuracy": round(float(average_accuracy), 2) if average_accuracy is not None else None,
        "average_score": round(float(average_score), 2) if average_score is not None else None,
        "best_score": round(float(best_score), 2) if best_score is not None else None,
        "latest_score": round(float(latest_attempt.score), 2) if latest_attempt else None,
        "projected_average_full_score": (
            round((float(average_accuracy) / 100) * full_max_score, 2)
            if average_accuracy is not None
            else None
        ),
        "full_max_score": full_max_score,
        "recent_attempts": [],
        "trend": TREND_NOT_ENOUGH_DATA,
        "strong_subjects": [],
        "weak_subjects": [],
        "weak_topics": [],
    }

    if user_id is not None:
        stats["recent_attempts"] = await get_recent_attempts(session, user_id, limit=3)
        stats["trend"] = await get_progress_trend(session, user_id)
        if profile:
            subject_performance = await get_subject_performance(session, user_id, profile, min_answers=2)
            stats["strong_subjects"] = subject_performance[:2]
            stats["weak_subjects"] = sorted(
                subject_performance,
                key=lambda item: (item["accuracy"], -item["total"], item["subject"]),
            )[:2]
        stats["weak_topics"] = (await get_topic_performance(session, user_id, min_answers=2))[:3]

    return stats


def format_statistics(stats: dict[str, object], language_code: str) -> str:
    if stats["total_attempts"] == 0:
        return t(language_code, "stats_empty")

    recent_lines = _format_recent_attempts(stats["recent_attempts"], language_code)
    subject_lines = _format_subject_sections(stats, language_code)
    topic_lines = _format_weak_topics(stats["weak_topics"], language_code)

    return (
        f"{t(language_code, 'stats_title')}\n\n"
        f"{t(language_code, 'total_attempts')}: {stats['total_attempts']}\n"
        f"{t(language_code, 'average_accuracy')}: {stats['average_accuracy']}%\n"
        f"{t(language_code, 'average_score')}: {stats['average_score']}\n"
        f"{t(language_code, 'best_score')}: {stats['best_score']}\n"
        f"{t(language_code, 'latest_score')}: {stats['latest_score']}\n"
        f"{t(language_code, 'projected_average_full_score')}: "
        f"{stats['projected_average_full_score']} / {stats['full_max_score']}\n\n"
        f"{t(language_code, 'recent_attempts')}\n"
        f"{recent_lines}\n\n"
        f"{t(language_code, 'progress_trend')}: {t(language_code, _trend_key(str(stats['trend'])))}\n\n"
        f"{subject_lines}\n\n"
        f"{topic_lines}"
    )


def _format_recent_attempts(attempts: object, language_code: str) -> str:
    if not isinstance(attempts, list) or not attempts:
        return t(language_code, "trend_not_enough_data")
    return "\n".join(
        f"{index}) {attempt['accuracy_percent']}% - {attempt['score']} {t(language_code, 'points')}"
        for index, attempt in enumerate(attempts, start=1)
    )


def _format_subject_sections(stats: dict[str, object], language_code: str) -> str:
    strong = stats.get("strong_subjects")
    weak = stats.get("weak_subjects")
    if not strong or not weak:
        return t(language_code, "not_enough_subject_data")

    strong_lines = [t(language_code, "strong_subjects")]
    strong_lines.extend(
        f"✅ {subject_name(language_code, item['subject'])} - {item['accuracy']}%"
        for item in strong
    )

    weak_lines = [t(language_code, "weak_subjects")]
    weak_lines.extend(
        f"⚠️ {subject_name(language_code, item['subject'])} - {item['accuracy']}%"
        for item in weak
    )
    return "\n".join(strong_lines + [""] + weak_lines)


def _format_weak_topics(topics: object, language_code: str) -> str:
    if not isinstance(topics, list) or not topics:
        return t(language_code, "not_enough_topic_data")

    lines = [t(language_code, "weak_topics")]
    lines.extend(
        f"⚠️ {item['subtopic'] or item['topic']} - {item['correct']}/{item['total']}"
        for item in topics
    )
    return "\n".join(lines)


def _trend_key(trend: str) -> str:
    return {
        TREND_IMPROVEMENT: "trend_improvement",
        TREND_DECLINE: "trend_decline",
        TREND_STABLE: "trend_stable",
        TREND_NOT_ENOUGH_DATA: "trend_not_enough_data",
    }.get(trend, "trend_stable")
