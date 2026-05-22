"""US1：data_import 單元測試。"""

from __future__ import annotations

import pytest

from matcher.errors import RosterDecodeError, RosterTypeError
from matcher.template import AttributeDecl
from matcher.data_import import coerce_value, detect_csv_encoding, resolve_header


# ── detect_csv_encoding ─────────────────────────────────────────────


def test_detect_utf8():
    enc, txt = detect_csv_encoding("姓名\n王老師\n".encode("utf-8"))
    assert enc == "utf-8"
    assert "王老師" in txt


def test_detect_utf8_sig():
    enc, txt = detect_csv_encoding("﻿姓名\n王老師\n".encode("utf-8-sig"))
    assert enc == "utf-8-sig"


def test_detect_cp950():
    enc, txt = detect_csv_encoding("姓名\n王老師\n".encode("cp950"))
    assert enc == "cp950"


def test_detect_unsupported_raises():
    with pytest.raises(RosterDecodeError):
        detect_csv_encoding("姓名\n王老師\n".encode("utf-16"))


# ── resolve_header ──────────────────────────────────────────────────


def test_resolve_exact_key():
    decls = (AttributeDecl(key="name", type="str", required=True),)
    assert resolve_header("name", decls).key == "name"


def test_resolve_alias():
    decls = (AttributeDecl(key="name", type="str", required=True, aliases=("姓名",)),)
    assert resolve_header("姓名", decls).key == "name"


def test_resolve_ascii_case_insensitive():
    decls = (AttributeDecl(key="name", type="str", required=True),)
    assert resolve_header("NAME", decls).key == "name"
    assert resolve_header("Name", decls).key == "name"


def test_resolve_strips_whitespace():
    decls = (AttributeDecl(key="name", type="str", required=True, aliases=("姓名",)),)
    assert resolve_header("  姓名  ", decls).key == "name"


def test_resolve_unknown_returns_none():
    decls = (AttributeDecl(key="name", type="str", required=True),)
    assert resolve_header("年齡", decls) is None


def test_resolve_chinese_strict():
    """中文嚴格相等：教師 ≠ 老師。"""
    decls = (AttributeDecl(key="name", type="str", required=True, aliases=("教師",)),)
    assert resolve_header("老師", decls) is None


# ── coerce_value ────────────────────────────────────────────────────


def _decl(t):
    return AttributeDecl(key="x", type=t, required=True)


def test_coerce_str():
    assert coerce_value("hello", _decl("str"), row_num=2) == "hello"
    assert coerce_value("  spaces  ", _decl("str"), row_num=2) == "spaces"
    assert coerce_value(None, _decl("str"), row_num=2) == ""


def test_coerce_int_ok():
    assert coerce_value("8", _decl("int"), row_num=2) == 8
    assert coerce_value(8, _decl("int"), row_num=2) == 8
    assert coerce_value("  12 ", _decl("int"), row_num=2) == 12


def test_coerce_int_fail():
    with pytest.raises(RosterTypeError) as exc:
        coerce_value("八年", _decl("int"), row_num=3)
    assert "八年" in str(exc.value)
    assert "第 3 列" in str(exc.value)


def test_coerce_int_empty_raises():
    with pytest.raises(RosterTypeError):
        coerce_value("", _decl("int"), row_num=2)
    with pytest.raises(RosterTypeError):
        coerce_value(None, _decl("int"), row_num=2)


def test_coerce_list_str_semicolon():
    assert coerce_value("G1;G2;G3", _decl("list_str"), row_num=2) == ["G1", "G2", "G3"]
    assert coerce_value("G1; G2 ;G3", _decl("list_str"), row_num=2) == ["G1", "G2", "G3"]
    assert coerce_value("", _decl("list_str"), row_num=2) == []
    assert coerce_value(None, _decl("list_str"), row_num=2) == []
