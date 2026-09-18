from app.auth.permissions import Role, has_permission


def test_cco_has_customer_pii_access():
    assert has_permission(Role.CCO, "customer_pii")


def test_aml_analyst_does_not_have_customer_pii_access():
    assert not has_permission(Role.AML_ANALYST, "customer_pii")


def test_aml_analyst_has_masked_customer_access():
    assert has_permission(Role.AML_ANALYST, "customer_masked")


def test_external_auditor_does_not_have_transaction_access():
    assert not has_permission(Role.EXTERNAL_AUDITOR, "transactions")


def test_relationship_manager_has_portfolio_access():
    assert has_permission(Role.RELATIONSHIP_MANAGER, "assigned_portfolio")
