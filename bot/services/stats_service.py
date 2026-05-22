from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import TestAttempt, User
from bot.locales import t


async def get_user_statistics(session: AsyncSession, telegram_id: int) -> dict[str, float | int | None]:
    user_id_subquery = select(User.id).where(User.telegram_id == telegram_id).scalar_subquery()

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
    }


def format_statistics(stats: dict[str, float | int | None], language_code: str) -> str:
    if stats["total_attempts"] == 0:
        return t(language_code, "stats_empty")

    return (
        f"{t(language_code, 'stats_title')}\n\n"
        f"{t(language_code, 'total_attempts')}: {stats['total_attempts']}\n"
        f"{t(language_code, 'average_accuracy')}: {stats['average_accuracy']}%\n"
        f"{t(language_code, 'average_score')}: {stats['average_score']}\n"
        f"{t(language_code, 'best_score')}: {stats['best_score']}\n"
        f"{t(language_code, 'latest_score')}: {stats['latest_score']}"
    )
