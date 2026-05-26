"""明確錯誤類別（對應 FR-011、contracts/cli.md 退出碼表）。"""

from __future__ import annotations


class MatcherError(Exception):
    """matcher 所有可預期錯誤的共同基底。"""

    exit_code: int = 1


class QualifiedSetEmpty(MatcherError):
    exit_code = 10

    def __init__(self, message: str, *, trace=None, rule_stats=None,
                 culprit=None, total_pairs: int = 0, rule_descriptions=None) -> None:
        super().__init__(message)
        # Feature 015：攜帶診斷，讓上層（CLI/Web）能解釋「哪條規則刷掉幾組」
        self.trace = trace or []
        self.rule_stats: dict = rule_stats or {}
        self.culprit = culprit
        self.total_pairs = total_pairs
        self.rule_descriptions: dict = rule_descriptions or {}


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


class RosterDecodeError(MatcherError):
    exit_code = 30


class RosterColumnMismatch(MatcherError):
    exit_code = 31


class RosterTypeError(MatcherError):
    exit_code = 32


class RosterSheetAmbiguous(MatcherError):
    exit_code = 33


class MechanismRequiresPreferences(MatcherError):
    """機制（M1 / M2 等）需要至少一位角色提供志願；通用化自階段 4a 的 M1RequiresPreferences。"""
    exit_code = 40


# 向後相容 alias（階段 4a 既有 import 與測試斷言皆可繼續運作）
M1RequiresPreferences = MechanismRequiresPreferences
