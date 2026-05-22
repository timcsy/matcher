"""明確錯誤類別（對應 FR-011、contracts/cli.md 退出碼表）。"""

from __future__ import annotations


class MatcherError(Exception):
    """matcher 所有可預期錯誤的共同基底。"""

    exit_code: int = 1


class QualifiedSetEmpty(MatcherError):
    exit_code = 10


class CapacityShortage(MatcherError):
    exit_code = 11


class RuleContradiction(MatcherError):
    exit_code = 12


class SeedMissing(MatcherError):
    exit_code = 13


class EmptyRoster(MatcherError):
    exit_code = 14


class DuplicateIdentity(MatcherError):
    exit_code = 15


class UnknownAttribute(MatcherError):
    exit_code = 16


class PreferencesNotSupported(MatcherError):
    exit_code = 17


class TemplateNotFound(MatcherError):
    exit_code = 20


class UnknownSchemaVersion(MatcherError):
    exit_code = 21


class TemplateMissingField(MatcherError):
    exit_code = 22


class TemplateConflict(MatcherError):
    exit_code = 23
