"""
Tests for project utilities.
"""
from datetime import date
from django.test import TestCase
from apps.projects.utils import subtract_working_days, sp_to_working_days


class WorkingDaysTestCase(TestCase):
    """Test working day calculation utilities."""

    def test_subtract_working_days_monday_minus_one(self):
        """Monday - 1 working day = Friday (skips weekend)."""
        result = subtract_working_days(date(2026, 6, 22), 1)  # Monday
        self.assertEqual(result, date(2026, 6, 19))  # Friday

    def test_subtract_working_days_friday_minus_two(self):
        """Friday - 2 working days = Wednesday."""
        result = subtract_working_days(date(2026, 6, 20), 2)  # Friday
        self.assertEqual(result, date(2026, 6, 18))  # Wednesday

    def test_subtract_working_days_zero(self):
        """Subtracting 0 working days returns same date."""
        test_date = date(2026, 6, 22)
        result = subtract_working_days(test_date, 0)
        self.assertEqual(result, test_date)

    def test_subtract_working_days_negative(self):
        """Subtracting negative working days returns same date."""
        test_date = date(2026, 6, 22)
        result = subtract_working_days(test_date, -5)
        self.assertEqual(result, test_date)

    def test_sp_to_working_days_eight_sp(self):
        """8 SP = 1 working day."""
        result = sp_to_working_days(8)
        self.assertEqual(result, 1)

    def test_sp_to_working_days_sixteen_sp(self):
        """16 SP = 2 working days."""
        result = sp_to_working_days(16)
        self.assertEqual(result, 2)

    def test_sp_to_working_days_four_sp(self):
        """4 SP rounds to 1 working day (minimum)."""
        result = sp_to_working_days(4)
        self.assertEqual(result, 1)

    def test_sp_to_working_days_twenty_sp(self):
        """20 SP = 2.5 days, rounds to 3 working days."""
        result = sp_to_working_days(20)
        self.assertEqual(result, 3)

    def test_sp_to_working_days_one_sp(self):
        """1 SP (minimum) = 1 working day."""
        result = sp_to_working_days(1)
        self.assertEqual(result, 1)
