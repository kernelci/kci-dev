#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from kcidev.api import KciDevError

STATUS_CHOICES = ("all", "pass", "fail", "inconclusive")


def checked_status(status):
    normalised = status.strip().lower()
    if normalised not in STATUS_CHOICES:
        raise KciDevError(
            f"Unknown status {status!r}: expected one of {', '.join(STATUS_CHOICES)}"
        )
    return normalised


def check_page_bounds(limit, offset):
    if limit < 0:
        raise KciDevError(f"Invalid limit {limit}: must be zero or greater")
    if offset < 0:
        raise KciDevError(f"Invalid offset {offset}: must be zero or greater")


def checked_filters(filters):
    for entry in filters or []:
        if "=" not in entry:
            raise KciDevError(
                f"Invalid filter {entry!r}: expected 'field=value', "
                "for example 'state=done'"
            )
    return list(filters or [])


def check_page_args(status, limit, offset):
    """Validate paging arguments before any request is made.

    The tools fetch a whole result set and page it in memory, so
    validating inside the pager would mean an expensive request for
    input that was never usable, and a request failure would mask the
    real complaint.
    """
    check_page_bounds(limit, offset)
    if status:
        checked_status(status)
