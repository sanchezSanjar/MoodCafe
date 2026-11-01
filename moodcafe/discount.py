"""Smile-for-a-discount rules: smooth the happy score, require a held smile, issue one-time coupons.

No images are stored; only the coupon code, discount and time are logged for the barista.
"""
import csv
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from .config import COUPONS_FILE

SMILE_THRESHOLD = 0.80   # smoothed happy probability that counts as a smile
HOLD_SECONDS = 1.5       # how long the smile must be held
SMOOTHING = 0.35         # weight of the newest frame in the moving average
COOLDOWN_SECONDS = 30    # pause after a coupon before the next one
AWAY_SECONDS = 2.0       # nobody in front of the camera this long = next customer
COUPON_MINUTES = 15
TIERS = [(0.95, 20), (0.88, 15), (0.0, 10)]  # (minimum peak score, discount %)
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I to avoid misreading


@dataclass
class Coupon:
    code: str
    percent: int
    issued: datetime
    expires: datetime


def discount_for(peak_score):
    return next(percent for minimum, percent in TIERS if peak_score >= minimum)


def new_code():
    return "MOOD-" + "".join(secrets.choice(CODE_ALPHABET) for _ in range(4))


class SmileJudge:
    """Feed it the main face's happy probability every frame; it decides when a coupon is earned."""

    def __init__(self, log_file=COUPONS_FILE):
        self.log_file = log_file
        self.score = 0.0          # smoothed happy probability
        self.smile_started = None
        self.peak = 0.0
        self.cooldown_until = None
        self.away_since = None
        self.needs_new_customer = False
        self.last_coupon = None

    @property
    def state(self):
        if self.cooldown_until is not None:
            return "cooldown"
        if self.needs_new_customer:
            return "next_customer"
        return "smiling" if self.smile_started is not None else "watching"

    def progress(self, now):
        """0..1 how far the current smile is towards a coupon."""
        if self.smile_started is None:
            return 0.0
        return min(1.0, (now - self.smile_started) / HOLD_SECONDS)

    def update(self, happy, now):
        """happy: probability for the main face, or None when no face is visible. Returns a Coupon when earned."""
        if happy is None:
            self.away_since = self.away_since or now
            if now - self.away_since >= AWAY_SECONDS:
                self.needs_new_customer = False
            self.score, self.smile_started, self.peak = 0.0, None, 0.0
            self._end_cooldown_if_due(now)
            return None

        self.away_since = None
        self.score = SMOOTHING * happy + (1 - SMOOTHING) * self.score
        self._end_cooldown_if_due(now)
        if self.cooldown_until is not None or self.needs_new_customer:
            return None

        if self.score >= SMILE_THRESHOLD:
            if self.smile_started is None:
                self.smile_started, self.peak = now, self.score
            self.peak = max(self.peak, self.score)
            if now - self.smile_started >= HOLD_SECONDS:
                return self._issue(now)
        else:
            self.smile_started, self.peak = None, 0.0
        return None

    def _end_cooldown_if_due(self, now):
        if self.cooldown_until is not None and now >= self.cooldown_until:
            self.cooldown_until = None

    def _issue(self, now):
        issued = datetime.now()
        coupon = Coupon(new_code(), discount_for(self.peak), issued, issued + timedelta(minutes=COUPON_MINUTES))
        self.last_coupon = coupon
        self.cooldown_until = now + COOLDOWN_SECONDS
        self.needs_new_customer = True
        self.smile_started, self.peak = None, 0.0
        self._log(coupon)
        return coupon

    def _log(self, coupon):
        if self.log_file is None:
            return
        new_file = not self.log_file.exists()
        with open(self.log_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if new_file:
                writer.writerow(["code", "discount_percent", "issued", "expires"])
            writer.writerow([coupon.code, coupon.percent, coupon.issued.isoformat(timespec="seconds"),
                             coupon.expires.isoformat(timespec="seconds")])
