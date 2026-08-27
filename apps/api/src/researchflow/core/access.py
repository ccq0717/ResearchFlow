import hashlib
import hmac
from collections.abc import Callable
from time import time


class DemoAccessGuard:
    cookie_name = "researchflow_demo_session"

    def __init__(
        self,
        access_code: str | None,
        *,
        secure_cookie: bool,
        session_ttl_seconds: int = 8 * 60 * 60,
        now: Callable[[], float] = time,
    ) -> None:
        self._access_code = access_code
        self.secure_cookie = secure_cookie
        self.cookie_same_site = "none" if secure_cookie else "lax"
        self.session_ttl_seconds = session_ttl_seconds
        self._now = now

    @property
    def enabled(self) -> bool:
        return self._access_code is not None

    def authenticate(self, candidate: str) -> bool:
        return self._access_code is None or hmac.compare_digest(candidate, self._access_code)

    def issue_session(self) -> str:
        if self._access_code is None:
            return ""
        issued_at = str(int(self._now()))
        return f"{issued_at}.{self._sign(issued_at)}"

    def allows(self, session_token: str | None) -> bool:
        if not self.enabled:
            return True
        if session_token is None or "." not in session_token:
            return False
        issued_at, signature = session_token.split(".", maxsplit=1)
        try:
            age = self._now() - int(issued_at)
        except ValueError:
            return False
        return -60 <= age <= self.session_ttl_seconds and hmac.compare_digest(
            signature, self._sign(issued_at)
        )

    def _sign(self, issued_at: str) -> str:
        if self._access_code is None:
            return ""
        return hmac.new(
            self._access_code.encode(),
            f"researchflow-demo-session:{issued_at}".encode(),
            hashlib.sha256,
        ).hexdigest()
