from __future__ import annotations

import sqlite3
import unicodedata
from difflib import SequenceMatcher


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return " ".join(
        "".join(char for char in decomposed if not unicodedata.combining(char))
        .casefold()
        .split()
    )


def _description_similarity(left: str, right: str) -> float:
    normalized_left = _normalize(left)
    normalized_right = _normalize(right)
    sequence = SequenceMatcher(None, normalized_left, normalized_right).ratio()
    left_tokens = set(normalized_left.split())
    right_tokens = set(normalized_right.split())
    token_overlap = (
        len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))
        if left_tokens and right_tokens
        else 0
    )
    contains = (
        0.92
        if normalized_left in normalized_right or normalized_right in normalized_left
        else 0
    )
    return max(sequence, token_overlap, contains)


def reconciliation_options(
    connection: sqlite3.Connection,
    transaction: dict,
    reserved: set[tuple[int, str]] | None = None,
) -> tuple[list[dict], int | None]:
    month = transaction["date"][:7]
    reserved = reserved or set()
    rows = connection.execute(
        """
        SELECT fixed.*
        FROM entries AS fixed
        WHERE fixed.entry_type = 'expense'
          AND fixed.recurring = 1
          AND fixed.start_month <= ?
          AND (fixed.end_month IS NULL OR fixed.end_month = '' OR fixed.end_month >= ?)
          AND NOT EXISTS (
              SELECT 1 FROM entries AS actual
              WHERE actual.reconciled_entry_id = fixed.id
                AND actual.start_month = ?
          )
        ORDER BY fixed.amount DESC
        """,
        (month, month, month),
    ).fetchall()

    scored = []
    for row in rows:
        if (row["id"], month) in reserved:
            continue
        description_score = _description_similarity(
            transaction["description"], row["description"]
        )
        amount_score = max(
            0,
            1
            - abs(transaction["amount"] - row["amount"])
            / max(transaction["amount"], row["amount"]),
        )
        same_category = transaction["category"] == row["category"]
        score = description_score * 0.5 + amount_score * 0.35
        if same_category:
            score += 0.25

        if same_category or description_score >= 0.32 or amount_score >= 0.82:
            scored.append(
                {
                    "entry_id": row["id"],
                    "description": row["description"],
                    "expected_amount": round(row["amount"], 2),
                    "score": round(min(score / 1.1, 1), 2),
                    "_raw_score": score,
                    "_description_score": description_score,
                    "_amount_score": amount_score,
                    "_same_category": same_category,
                }
            )

    scored.sort(key=lambda option: option["_raw_score"], reverse=True)
    suggested_id = None
    if scored:
        best = scored[0]
        second_score = scored[1]["_raw_score"] if len(scored) > 1 else 0
        strong_match = (
            best["_raw_score"] >= 0.68
            and (
                best["_raw_score"] - second_score >= 0.08
                or best["_description_score"] >= 0.72
                or (best["_same_category"] and best["_amount_score"] >= 0.95)
            )
        )
        if strong_match:
            suggested_id = best["entry_id"]

    public_options = [
        {
            "entry_id": option["entry_id"],
            "description": option["description"],
            "expected_amount": option["expected_amount"],
            "confidence": option["score"],
        }
        for option in scored[:5]
    ]
    return public_options, suggested_id

