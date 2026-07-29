"""Validation and release gates."""

from __future__ import annotations


def validate_contract(*args, **kwargs):
    from algolab.verification.contract_validator import validate_contract as _validate_contract

    return _validate_contract(*args, **kwargs)

__all__ = ["validate_contract"]
