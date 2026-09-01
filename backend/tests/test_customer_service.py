from app.services import customer_service


def test_mock_profile_changes_are_persisted_without_dynamodb(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(customer_service, "DATA_SOURCE", "mock")
    monkeypatch.setenv("FUTURE_YOU_MOCK_STATE_DIR", str(tmp_path))

    profile = customer_service.get_customer("alex")
    assert profile is not None
    updated = profile.model_copy(update={"currentBalance": 7777})

    customer_service.save_customer_profile(updated)

    reloaded = customer_service.get_customer("alex")
    assert reloaded is not None
    assert reloaded.currentBalance == 7777
    assert (tmp_path / "alex.json").exists()


def test_mock_profile_uses_fixture_when_no_local_state_exists(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(customer_service, "DATA_SOURCE", "mock")
    monkeypatch.setenv("FUTURE_YOU_MOCK_STATE_DIR", str(tmp_path))

    profile = customer_service.get_customer("alex")

    assert profile is not None
    assert profile.monthlyIncome == 5200
    assert list(tmp_path.iterdir()) == []
