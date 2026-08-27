import hashlib
import hmac


class DemoAccessGuard:
    cookie_name = "researchflow_demo_session"

    def __init__(self, access_code: str | None, *, secure_cookie: bool) -> None:
        self._access_code = access_code
        self.secure_cookie = secure_cookie
        self.session_token = (
            hmac.new(
                access_code.encode(),
                b"researchflow-demo-session",
                hashlib.sha256,
            ).hexdigest()
            if access_code
            else ""
        )

    @property
    def enabled(self) -> bool:
        return self._access_code is not None

    def authenticate(self, candidate: str) -> bool:
        return self._access_code is None or hmac.compare_digest(candidate, self._access_code)

    def allows(self, session_token: str | None) -> bool:
        return not self.enabled or (
            session_token is not None and hmac.compare_digest(session_token, self.session_token)
        )
