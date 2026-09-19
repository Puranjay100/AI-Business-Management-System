"""AuthManager — wraps streamlit-authenticator for role-aware login."""

from __future__ import annotations

from typing import Optional

import streamlit as st
import streamlit_authenticator as stauth  # type: ignore[import]
import yaml
from yaml.loader import SafeLoader


class AuthManager:
    """Provides login widget and role helpers backed by a YAML credential store.

    Passwords in ``credentials.yaml`` are stored in plain text the first time,
    then auto-hashed by streamlit-authenticator on first load (``auto_hash=True``).

    Parameters
    ----------
    credentials_path:
        Path to the ``credentials.yaml`` file.
    """

    def __init__(self, credentials_path: str = "credentials.yaml") -> None:
        self._credentials_path = credentials_path
        with open(credentials_path) as fh:
            self._config: dict = yaml.load(fh, Loader=SafeLoader)

        self._authenticator = stauth.Authenticate(
            credentials=self._config["credentials"],
            cookie_name=self._config["cookie"]["name"],
            cookie_key=self._config["cookie"]["key"],
            cookie_expiry_days=self._config["cookie"]["expiry_days"],
            auto_hash=True,
        )

    def render_login_widget(self) -> tuple[Optional[str], Optional[bool], Optional[str]]:
        """Render the login form and return *(name, auth_status, username)*.

        *auth_status* is:
        - ``True``  — successfully authenticated
        - ``False`` — wrong password
        - ``None``  — form not yet submitted
        """
        result = self._authenticator.login(location="main")
        if result is None:
            # Auth already stored in session state from a cookie
            return (
                st.session_state.get("name"),
                st.session_state.get("authentication_status"),
                st.session_state.get("username"),
            )
        name, auth_status, username = result
        return name, auth_status, username

    def render_logout_button(self, location: str = "sidebar") -> None:
        """Render the streamlit-authenticator logout button."""
        self._authenticator.logout(location=location)

    def get_role(self, username: str) -> str:
        """Return the role string for *username* (``"admin"`` or ``"staff"``).

        Falls back to ``"staff"`` if the role key is absent.
        """
        users = self._config["credentials"].get("usernames", {})
        return users.get(username, {}).get("role", "staff")

    def is_admin(self, username: str) -> bool:
        """Return True if *username* has the ``"admin"`` role."""
        return self.get_role(username) == "admin"
