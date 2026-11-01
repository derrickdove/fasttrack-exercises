"""Recorded network evidence only: no shell commands or live connections."""

import hashlib
from pathlib import Path

import pytest

from starter.network_diagnosis import diagnose_network


DATA = Path(__file__).resolve().parents[1] / "data"
# Compare fingerprints in a helper, then assert a boolean so pytest cannot
# print keyed answer values. The last case has no README evidence preview.
ANSWER_DIGESTS: dict[str, dict[str, str]] = {
    "case_a": {
        "diagnosis": "0f6c1a3479cf2c8d3585d4cd82cd09c39dec525d5c96292c7ed1b30368ded682",
        "fix": "652e164840b03024e6a87f86c843a60896d7c9fb07f8d2314a0bc74588b2f917"
    },
    "case_b": {
        "diagnosis": "7eada30489a2bd11a9cd496788728f753022b107f4d98bfdd678a5740baedba1",
        "fix": "4af568dcb8f8c12111eae94f76d75de04aceed550ef85f17d84597ca9c146dde"
    },
    "case_c": {
        "diagnosis": "db848203d63d3538c37dfaa243ae86ad135c58bce588f36e78013ac2eeab9ad5",
        "fix": "b75005b7b5ae18ce19f3dfe4ea52d3f6840ec12f42def71c386597db44b64d8d"
    },
    "case_d": {
        "diagnosis": "7ab1bd1ca1c39b0fe4ea6ec0a8b9d800441b15a7730c3c10bf3182374859ed94",
        "fix": "17dab5fad2c715ff0793f9b1eebbedfff864ea94121828a2dbe2cda9883885ee"
    },
    "case_e": {
        "diagnosis": "594f4fb152742fd4ff50c80b1bbac43b7f252cc31d15a8e23a362279f34617eb",
        "fix": "689bef85a2d808029ffbeadf2cc5fadda416ecea69a4a003a143b06950355d50"
    }
}


def field_is_correct(answers: object, case: str, field: str) -> bool:
    __tracebackhide__ = True
    if not isinstance(answers, dict):
        return False
    diagnosis = answers.get(case)
    if not isinstance(diagnosis, dict):
        return False
    value = diagnosis.get(field)
    if not isinstance(value, str):
        return False
    return hashlib.sha256(value.encode("utf-8")).hexdigest() == ANSWER_DIGESTS[case][field]


def test_e5_answer_shape() -> None:
    answers = diagnose_network()
    assert isinstance(answers, dict), "E5: return a dictionary; reread Contract"
    assert set(answers) == {path.stem for path in DATA.glob("*.txt")}, "E5: include every recorded case"
    assert len({id(value) for value in answers.values()}) == len(answers), "E5: give each case its own dictionary"
    for diagnosis in answers.values():
        assert isinstance(diagnosis, dict), "E5: each case needs a dictionary"
        assert set(diagnosis) == {"diagnosis", "fix"}, "E5: use exactly the two documented fields"
        assert all(isinstance(value, str) for value in diagnosis.values()), "E5: values must be strings"


@pytest.mark.parametrize("case", ["case_a", "case_b", "case_c", "case_d"])
def test_e5_diagnosis_from_both_endpoints(case: str) -> None:
    correct = field_is_correct(diagnose_network(), case, "diagnosis")
    assert correct, "E5: compare approved addressing, routes, requested port, listeners, and the connection error"


@pytest.mark.parametrize("case", ["case_a", "case_b", "case_c", "case_d"])
def test_e5_fix_matches_evidence(case: str) -> None:
    correct = field_is_correct(diagnose_network(), case, "fix")
    assert correct, "E5: choose the smallest documented next action supported by the capture"


def test_e5_additional_capture() -> None:
    answers = diagnose_network()
    correct = all(field_is_correct(answers, "case_e", field) for field in ("diagnosis", "fix"))
    assert correct, "E5: inspect the additional data capture; distinguish recorded facts from an unproved cause"
