from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import TestAttempt, User


async def get_user_statistics(session: AsyncSession, telegram_id: int) -> dict[str, float | int | None]:
    user_id_subquery = select(User.id).where(User.telegram_id == telegram_id).scalar_subquery()

    summary_result = await session.execute(
        select(
            func.count(TestAttempt.id),
            func.avg(TestAttempt.accuracy_percent),
            func.max(TestAttempt.accuracy_percent),
        ).where(TestAttempt.user_id == user_id_subquery)
    )
    total_attempts, average_accuracy, best_result = summary_result.one()

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
        "best_result": round(float(best_result), 2) if best_result is not None else None,
        "latest_result": round(float(latest_attempt.accuracy_percent), 2) if latest_attempt else None,
    }


def format_statistics(stats: dict[str, float | int | None]) -> str:
    if stats["total_attempts"] == 0:
        return "You do not have quiz attempts yet. Start a quiz first, then come back here."

    return (
        "My statistics\n\n"
        f"Total attempts: {stats['total_attempts']}\n"
        f"Average accuracy: {stats['average_accuracy']}%\n"
        f"Best result: {stats['best_result']}%\n"
        f"Latest result: {stats['latest_result']}%"
    )
