#!/usr/bin/env python3
"""Deterministic 180-day capacity simulation based on scheduler.py and service.py."""

from __future__ import annotations

import heapq
import random
from dataclasses import dataclass
from datetime import date, timedelta


DAYS = 180
START = date(2026, 1, 5)


@dataclass
class Card:
    due_day: int
    interval_hours: float = 0


def next_days(interval_hours: float, rating: str) -> tuple[int, float]:
    if rating == "again":
        hours = 0.5
    elif rating == "hard":
        hours = max(12, round(max(interval_hours, 8) * 1.5))
    else:
        steps = (24, 72, 168, 336, 720, 1440)
        hours = next((step for step in steps if step > interval_hours), min(4320, round(interval_hours * 1.5)))
    # With only fixed daily sessions, sub-day due times are effectively next-session/day work.
    return max(1, (int(hours) + 23) // 24), hours


def simulate(name: str, probabilities: tuple[float, float, float], behavior: str) -> dict[str, object]:
    rng = random.Random(f"{name}:{behavior}:20261028")
    queue: list[tuple[int, int, Card]] = []
    serial = 0
    unseen_stranded = 0
    rows = []
    divergence = None
    for day in range(DAYS):
        current = START + timedelta(days=day)
        due_cards = []
        while queue and queue[0][0] <= day:
            due_cards.append(heapq.heappop(queue)[2])
        due_count = len(due_cards)
        new_offered = 30 if due_count < 10 else 20 if due_count < 30 else 10
        missed = behavior == "two_days_week" and current.weekday() in {1, 4}
        missed = missed or behavior == "two_week_gap" and 60 <= day < 74
        capacity = 0 if missed else (52 if current.weekday() == 6 else 24)
        reviewed_due = min(due_count, capacity)
        remaining_capacity = capacity - reviewed_due
        first_seen = min(new_offered, remaining_capacity)
        unseen_stranded += new_offered - first_seen
        leftovers = due_cards[reviewed_due:]
        for card in leftovers:
            serial += 1
            heapq.heappush(queue, (day + 1, serial, card))
        review_cards = due_cards[:reviewed_due] + [Card(day) for _ in range(first_seen)]
        for card in review_cards:
            x = rng.random()
            good, hard, again = probabilities
            rating = "good" if x < good else "hard" if x < good + hard else "again"
            delay, interval = next_days(card.interval_hours, rating)
            card.interval_hours = interval
            card.due_day = day + delay
            serial += 1
            heapq.heappush(queue, (card.due_day, serial, card))
        end_debt = len(leftovers)
        if divergence is None and end_debt > 0:
            divergence = current.isoformat()
        rows.append((current.isoformat(), new_offered, due_count, capacity, reviewed_due + first_seen, end_debt, unseen_stranded))
    return {"name": name, "behavior": behavior, "rows": rows, "divergence": divergence, "final_queue": len(queue), "stranded": unseen_stranded}


def main() -> None:
    scenarios = [
        ("85/10/5", (0.85, 0.10, 0.05)),
        ("70/20/10", (0.70, 0.20, 0.10)),
    ]
    for label, probabilities in scenarios:
        for behavior in ("perfect", "two_days_week", "two_week_gap"):
            result = simulate(label, probabilities, behavior)
            rows = result["rows"]
            peak_due = max(row[2] for row in rows)
            peak_debt = max(row[5] for row in rows)
            minutes_avg = sum(row[4] for row in rows) / DAYS * 6.5 / 60
            print(
                f"scenario={label} behavior={behavior} divergence={result['divergence']} "
                f"peak_due={peak_due} peak_review_debt={peak_debt} final_scheduled={result['final_queue']} "
                f"stranded_new={result['stranded']} avg_minutes={minutes_avg:.1f}"
            )
            print("date,new,due,capacity,reviewed,debt,stranded")
            for row in rows[:7] + rows[56:77] + rows[-7:]:
                print(",".join(map(str, row)))


if __name__ == "__main__":
    main()
