import tempfile
import unittest
from pathlib import Path

from moodcafe.discount import (AWAY_SECONDS, CODE_ALPHABET, COOLDOWN_SECONDS, HOLD_SECONDS, SmileJudge,
                               discount_for)

FPS = 20


def run(judge, happy, seconds, start):
    """Feed the same happy value for some seconds at FPS; return (coupons, end time)."""
    coupons, t = [], start
    for _ in range(int(seconds * FPS)):
        t += 1 / FPS
        coupon = judge.update(happy, t)
        if coupon:
            coupons.append(coupon)
    return coupons, t


class SmileJudgeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = Path(self.tmp.name) / "coupons.csv"
        self.judge = SmileJudge(log_file=self.log)

    def tearDown(self):
        self.tmp.cleanup()

    def test_held_smile_earns_one_coupon(self):
        coupons, _ = run(self.judge, 0.99, HOLD_SECONDS + 2, 0)
        self.assertEqual(len(coupons), 1)
        self.assertEqual(coupons[0].percent, 20)
        self.assertRegex(coupons[0].code, f"^MOOD-[{CODE_ALPHABET}]{{4}}$")
        self.assertIn(coupons[0].code, self.log.read_text())

    def test_neutral_face_gets_nothing(self):
        coupons, _ = run(self.judge, 0.2, 10, 0)
        self.assertEqual(coupons, [])
        self.assertEqual(self.judge.state, "watching")

    def test_short_smile_is_not_enough(self):
        coupons, t = run(self.judge, 0.99, HOLD_SECONDS - 0.5, 0)
        more, _ = run(self.judge, 0.1, 2, t)  # stops smiling: progress resets
        self.assertEqual(coupons + more, [])
        self.assertEqual(self.judge.progress(t + 2), 0.0)

    def test_single_spike_is_smoothed_away(self):
        self.judge.update(1.0, 0.0)
        self.assertLess(self.judge.score, 0.5)

    def test_same_person_cannot_repeat(self):
        first, t = run(self.judge, 0.99, HOLD_SECONDS + 1, 0)
        again, t = run(self.judge, 0.99, COOLDOWN_SECONDS + 5, t)  # keeps smiling, never leaves
        self.assertEqual(len(first), 1)
        self.assertEqual(again, [])
        self.assertEqual(self.judge.state, "next_customer")

    def test_next_customer_after_leaving_and_cooldown(self):
        _, t = run(self.judge, 0.99, HOLD_SECONDS + 1, 0)
        _, t = run(self.judge, None, max(AWAY_SECONDS, COOLDOWN_SECONDS) + 1, t)  # person leaves
        coupons, _ = run(self.judge, 0.99, HOLD_SECONDS + 1, t)
        self.assertEqual(len(coupons), 1)

    def test_discount_tiers(self):
        self.assertEqual(discount_for(0.97), 20)
        self.assertEqual(discount_for(0.90), 15)
        self.assertEqual(discount_for(0.81), 10)


if __name__ == "__main__":
    unittest.main()
