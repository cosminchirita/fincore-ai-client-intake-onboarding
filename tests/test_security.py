from app.security import pseudonymize, safe_filename


def test_pseudonymization_is_deterministic_and_not_plaintext():
    first = pseudonymize("192.0.2.1")
    second = pseudonymize("192.0.2.1")
    assert first == second
    assert first != "192.0.2.1"
    assert len(first) == 64


def test_safe_filename_removes_path_traversal():
    assert safe_filename("../../invoice demo.pdf") == "invoicedemo.pdf"
