from researchflow.core.access import DemoAccessGuard


def test_demo_session_signature_expires_on_the_server() -> None:
    current_time = [1_000_000.0]
    guard = DemoAccessGuard(
        "long-demo-secret",
        secure_cookie=False,
        session_ttl_seconds=60,
        now=lambda: current_time[0],
    )
    token = guard.issue_session()

    assert guard.allows(token)
    current_time[0] += 61
    assert not guard.allows(token)
    assert not guard.allows(token + "tampered")
