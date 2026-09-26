from slotfill.data import rows
from slotfill.extract import Trained, roles_from_gold, rules
from slotfill.schema import parse_amount, parse_date, same, validate

R = {"id": "t", "gold": {"company": "ACME TRADING SDN BHD", "date": "25/12/2018", "address": "NO 5, JALAN SAGU, 81100 JOHOR",
                         "total": "9.00"},
     "lines": rows([("ACME TRADING SDN BHD", (10, 10, 200, 30)), ("NO 5, JALAN SAGU,", (10, 40, 200, 60)),
                    ("81100 JOHOR", (10, 70, 200, 90)), ("TEL: 07-1234567", (10, 100, 200, 120)),
                    ("DATE: 25/12/2018", (10, 130, 200, 150)), ("SUBTOTAL", (10, 160, 80, 180)), ("8.49", (150, 160, 200, 180)),
                    ("TOTAL", (10, 190, 80, 210)), ("9.00", (150, 191, 200, 211))])}


def test_same_row_boxes_join():
    assert [t for t, _ in R["lines"]][-2:] == ["SUBTOTAL 8.49", "TOTAL 9.00"]


def test_schema_is_strict():
    assert parse_date("25 DEC 2018") == parse_date("25/12/2018") == parse_date("2018-12-25") == "2018-12-25"
    assert parse_date("31/02/2018") is None and parse_amount("RM 1,234.50") == "1234.50"
    assert validate({"company": "A", "address": "B", "date": "2018-12-25", "total": "9.00"}) == (True, [])
    ok, errors = validate({"company": "", "address": "B", "date": "25/12/2018", "total": "9"})
    assert not ok and len(errors) == 3
    assert same("company", "acme trading sdn bhd.", "ACME TRADING SDN BHD") and same("total", "9.00", "9")


def test_rules_and_trained_extract_the_schema():
    x = rules(R)
    assert x == {"company": "ACME TRADING SDN BHD", "date": "2018-12-25", "address": "NO 5, JALAN SAGU, 81100 JOHOR", "total": "9.00"}
    assert roles_from_gold(R)[:3] == ["company", "address", "address"] and roles_from_gold(R)[-1] == "total"
    model = Trained().fit([R] * 5)
    y = model(R)
    assert y["date"] == "2018-12-25" and y["total"] == "9.00" and validate(y)[0]
