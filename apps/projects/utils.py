"""
Utility functions for project and task calculations.
"""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


def subtract_working_days(end_date: date, working_days: int) -> date:
    """
    Zieht `working_days` Arbeitstage von `end_date` ab.
    Überspringt Samstag (5) und Sonntag (6).

    Beispiele:
        subtract_working_days(date(2026, 6, 22), 1)  # Montag - 1 AT = Freitag
        → date(2026, 6, 19)
        subtract_working_days(date(2026, 6, 20), 2)  # Freitag - 2 AT = Mittwoch
        → date(2026, 6, 18)
    """
    if working_days <= 0:
        return end_date

    current = end_date
    days_counted = 0

    while days_counted < working_days:
        current -= timedelta(days=1)
        if current.weekday() < 5:  # 0=Mo, 4=Fr, 5=Sa, 6=So
            days_counted += 1

    return current


def sp_to_working_days(story_points: float) -> int:
    """
    Rechnet Story Points in Arbeitstage um.
    1 SP = 1 Stunde, 8 SP = 1 Arbeitstag.
    Minimum: 1 Arbeitstag (auch bei < 8 SP).
    """
    days = Decimal(str(story_points)) / Decimal('8')
    rounded = int(days.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return max(1, rounded)
