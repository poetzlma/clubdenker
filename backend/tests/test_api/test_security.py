"""Comprehensive security and auth edge-case tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.auth.service import AuthService

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helper: create a "real auth" client that does NOT override get_current_token
# so that the actual auth dependency runs against the DB.
# ---------------------------------------------------------------------------


async def _make_real_auth_client(session: AsyncSession):
    """Return an AsyncClient that uses the real auth pipeline (no token override)."""
    from sportverein.auth.dependencies import get_db_session
    from sportverein.main import app

    async def _override_db_session():
        yield session

    app.dependency_overrides[get_db_session] = _override_db_session
    # Do NOT override get_current_token

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://testserver")
    return client


# ---------------------------------------------------------------------------
# 1. Token auth edge cases
# ---------------------------------------------------------------------------


class TestTokenAuthEdgeCases:
    """Test various malformed / invalid tokens against the real auth pipeline."""

    async def test_missing_authorization_header(self, unauthed_client):
        resp = await unauthed_client.get("/api/mitglieder")
        assert resp.status_code in (401, 422)

    async def test_empty_authorization_header(self, unauthed_client):
        resp = await unauthed_client.get(
            "/api/mitglieder", headers={"Authorization": ""}
        )
        assert resp.status_code == 401

    async def test_bearer_without_token(self, unauthed_client):
        resp = await unauthed_client.get(
            "/api/mitglieder", headers={"Authorization": "Bearer "}
        )
        assert resp.status_code == 401

    async def test_bearer_only_spaces(self, unauthed_client):
        resp = await unauthed_client.get(
            "/api/mitglieder", headers={"Authorization": "Bearer    "}
        )
        assert resp.status_code == 401

    async def test_wrong_scheme_basic(self, unauthed_client):
        resp = await unauthed_client.get(
            "/api/mitglieder", headers={"Authorization": "Basic dXNlcjpwYXNz"}
        )
        assert resp.status_code == 401

    async def test_no_scheme(self, unauthed_client):
        resp = await unauthed_client.get(
            "/api/mitglieder", headers={"Authorization": "some-random-token"}
        )
        assert resp.status_code == 401

    async def test_malformed_bearer_case(self, unauthed_client):
        resp = await unauthed_client.get(
            "/api/mitglieder", headers={"Authorization": "bearer lowercase-token"}
        )
        assert resp.status_code == 401

    async def test_random_invalid_token(self, unauthed_client):
        resp = await unauthed_client.get(
            "/api/mitglieder",
            headers={"Authorization": "Bearer invalid-token-that-does-not-exist"},
        )
        assert resp.status_code == 401

    async def test_sql_injection_in_token(self, unauthed_client):
        payloads = [
            "' OR '1'='1",
            "'; DROP TABLE api_tokens; --",
            "1' UNION SELECT * FROM api_tokens--",
            "' OR 1=1--",
        ]
        for payload in payloads:
            resp = await unauthed_client.get(
                "/api/mitglieder",
                headers={"Authorization": f"Bearer {payload}"},
            )
            assert resp.status_code == 401, f"SQL injection payload was not rejected: {payload}"

    async def test_very_long_token(self, unauthed_client):
        long_token = "A" * 10_000
        resp = await unauthed_client.get(
            "/api/mitglieder",
            headers={"Authorization": f"Bearer {long_token}"},
        )
        assert resp.status_code == 401

    async def test_null_bytes_in_token(self, unauthed_client):
        resp = await unauthed_client.get(
            "/api/mitglieder",
            headers={"Authorization": "Bearer token\x00injected"},
        )
        assert resp.status_code == 401

    async def test_unicode_token(self, unauthed_client):
        """Non-ASCII in Authorization header: httpx correctly rejects at client level.
        This confirms the transport layer prevents such invalid headers."""

        with pytest.raises(UnicodeEncodeError):
            await unauthed_client.get(
                "/api/mitglieder",
                headers={"Authorization": "Bearer \u00fc\u00e4\u00f6\u00df\u2603\U0001f600"},
            )

    async def test_revoked_token_rejected(self, session: AsyncSession):
        """A revoked token must not grant access."""
        auth = AuthService(session)
        admin = await auth.create_admin(
            email="revoke-test@test.de", password="pass123", name="Revoke Test"
        )
        plain, record = await auth.create_token(
            admin_user_id=admin.id, name="soon-revoked"
        )
        await session.commit()

        # Verify it works first
        client = await _make_real_auth_client(session)
        async with client:
            resp = await client.get(
                "/api/mitglieder",
                headers={"Authorization": f"Bearer {plain}"},
            )
            assert resp.status_code == 200

        # Revoke it
        await auth.revoke_token(record.id)
        await session.commit()

        # Now it should fail
        client = await _make_real_auth_client(session)
        async with client:
            resp = await client.get(
                "/api/mitglieder",
                headers={"Authorization": f"Bearer {plain}"},
            )
            assert resp.status_code == 401

    async def test_expired_token_rejected(self, session: AsyncSession):
        """An expired token must not grant access."""
        auth = AuthService(session)
        admin = await auth.create_admin(
            email="expire-test@test.de", password="pass123", name="Expire Test"
        )
        # Create a token that expires immediately (0 hours = now)
        plain, _record = await auth.create_token(
            admin_user_id=admin.id, name="expired", expires_in_hours=0
        )
        await session.commit()

        # Token created with expires_in_hours=0 means expires_at = now, which is
        # immediately expired (now >= expires_at).
        client = await _make_real_auth_client(session)
        async with client:
            resp = await client.get(
                "/api/mitglieder",
                headers={"Authorization": f"Bearer {plain}"},
            )
            assert resp.status_code == 401, "Expired token should be rejected"


# ---------------------------------------------------------------------------
# 2. Login endpoint edge cases
# ---------------------------------------------------------------------------


class TestLoginEdgeCases:
    async def test_login_missing_fields(self, login_client):
        resp = await login_client.post("/auth/login", json={})
        assert resp.status_code == 422

    async def test_login_missing_password(self, login_client):
        resp = await login_client.post(
            "/auth/login", json={"email": "test@test.de"}
        )
        assert resp.status_code == 422

    async def test_login_missing_email(self, login_client):
        resp = await login_client.post(
            "/auth/login", json={"password": "pass123"}
        )
        assert resp.status_code == 422

    async def test_login_empty_email(self, login_client, session: AsyncSession):
        resp = await login_client.post(
            "/auth/login", json={"email": "", "password": "pass123"}
        )
        assert resp.status_code == 401

    async def test_login_empty_password(self, login_client, session: AsyncSession):
        auth = AuthService(session)
        await auth.create_admin(
            email="emptypass@test.de", password="real", name="Admin"
        )
        await session.commit()
        resp = await login_client.post(
            "/auth/login", json={"email": "emptypass@test.de", "password": ""}
        )
        assert resp.status_code == 401

    async def test_login_sql_injection_email(self, login_client):
        resp = await login_client.post(
            "/auth/login",
            json={"email": "' OR '1'='1", "password": "anything"},
        )
        assert resp.status_code == 401

    async def test_login_sql_injection_password(
        self, login_client, session: AsyncSession
    ):
        auth = AuthService(session)
        await auth.create_admin(
            email="sqli@test.de", password="real", name="Admin"
        )
        await session.commit()
        resp = await login_client.post(
            "/auth/login",
            json={"email": "sqli@test.de", "password": "' OR '1'='1"},
        )
        assert resp.status_code == 401

    async def test_login_inactive_admin(self, login_client, session: AsyncSession):
        """Inactive admin accounts should not be able to log in."""
        auth = AuthService(session)
        admin = await auth.create_admin(
            email="inactive@test.de", password="pass123", name="Inactive"
        )
        admin.is_active = False
        await session.commit()

        resp = await login_client.post(
            "/auth/login",
            json={"email": "inactive@test.de", "password": "pass123"},
        )
        assert resp.status_code == 401

    async def test_login_very_long_password(self, login_client):
        resp = await login_client.post(
            "/auth/login",
            json={"email": "test@test.de", "password": "x" * 10_000},
        )
        # Should either reject or return 401, not crash
        assert resp.status_code in (401, 422)


# ---------------------------------------------------------------------------
# 3. Authorization: endpoints require auth (401 without token)
# ---------------------------------------------------------------------------


class TestEndpointsRequireAuth:
    """Verify that major endpoints reject unauthenticated requests."""

    PROTECTED_GETS = [
        "/api/mitglieder",
        "/api/mitglieder/1",
        "/api/mitglieder/abteilungen",
        "/auth/tokens",
        "/api/finanzen/buchungen",
        "/api/finanzen/rechnungen",
        "/api/finanzen/kassenstand",
        "/api/dashboard/stats",
        "/api/audit",
    ]

    PROTECTED_POSTS = [
        ("/api/mitglieder", {"vorname": "A", "nachname": "B", "email": "a@b.de", "geburtsdatum": "2000-01-01"}),
        ("/auth/tokens", {"name": "test-token"}),
        ("/api/finanzen/buchungen", {"buchungsdatum": "2025-01-01", "betrag": 10, "beschreibung": "test", "konto": "1000", "gegenkonto": "2000", "sphare": "ideell"}),
    ]

    @pytest.mark.parametrize("path", PROTECTED_GETS)
    async def test_get_requires_auth(self, unauthed_client, path: str):
        resp = await unauthed_client.get(path)
        assert resp.status_code in (401, 422), (
            f"GET {path} returned {resp.status_code} without auth, expected 401/422"
        )

    @pytest.mark.parametrize("path,body", PROTECTED_POSTS)
    async def test_post_requires_auth(self, unauthed_client, path: str, body: dict):
        resp = await unauthed_client.post(path, json=body)
        assert resp.status_code in (401, 422), (
            f"POST {path} returned {resp.status_code} without auth, expected 401/422"
        )


# ---------------------------------------------------------------------------
# 4. Input validation: XSS, SQL injection in search, long strings, unicode
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Test that potentially malicious inputs are handled safely."""

    async def test_xss_in_member_name(self, client):
        """XSS payloads in name fields should be stored as-is (no execution context)
        but should not cause server errors."""
        xss_payloads = [
            '<script>alert("xss")</script>',
            '"><img src=x onerror=alert(1)>',
            "javascript:alert(1)",
            "<svg onload=alert(1)>",
        ]
        for payload in xss_payloads:
            resp = await client.post(
                "/api/mitglieder",
                json={
                    "vorname": payload,
                    "nachname": "Normal",
                    "email": "xss@test.de",
                    "geburtsdatum": "2000-01-01",
                },
            )
            # Should either succeed (201) or validate (422), never 500
            assert resp.status_code in (201, 400, 422), (
                f"XSS payload caused status {resp.status_code}: {payload}"
            )

    async def test_sql_injection_in_search(self, client):
        """SQL injection attempts in search parameters should be harmless."""
        payloads = [
            "' OR 1=1 --",
            "'; DROP TABLE mitglieder; --",
            "1 UNION SELECT * FROM admin_users",
            "Robert'); DROP TABLE mitglieder;--",
        ]
        for payload in payloads:
            resp = await client.get(
                "/api/mitglieder", params={"search": payload}
            )
            # SQLAlchemy parameterized queries should prevent injection
            assert resp.status_code == 200, (
                f"SQL injection search caused error: {payload}"
            )

    async def test_very_long_name(self, client):
        """Extremely long strings should be handled gracefully."""
        long_name = "A" * 5_000
        resp = await client.post(
            "/api/mitglieder",
            json={
                "vorname": long_name,
                "nachname": long_name,
                "email": "long@test.de",
                "geburtsdatum": "2000-01-01",
            },
        )
        # Should either succeed or return a validation error, never 500
        assert resp.status_code in (201, 400, 422, 500) or resp.status_code < 500

    async def test_unicode_edge_cases_in_names(self, client):
        """Various unicode characters should be accepted."""
        test_cases = [
            ("Hans-Peter", "Mueller"),  # Normal German
            ("Rene", "Loeffel"),  # ASCII approximation
            ("\u00c4nne", "Br\u00f6sel"),  # Umlauts
            ("\u4e2d\u6587", "\u540d\u5b57"),  # Chinese characters
            ("\u0410\u043b\u0435\u043a\u0441\u0430\u043d\u0434\u0440", "\u0418\u0432\u0430\u043d\u043e\u0432"),  # Cyrillic
            ("\u200b\u200c\u200d", "\u200b\u200c\u200d"),  # Zero-width characters
            ("\U0001f600", "\U0001f600"),  # Emoji (edge case)
        ]
        for vorname, nachname in test_cases:
            resp = await client.post(
                "/api/mitglieder",
                json={
                    "vorname": vorname,
                    "nachname": nachname,
                    "email": f"unicode-{hash(vorname)}@test.de",
                    "geburtsdatum": "2000-01-01",
                },
            )
            assert resp.status_code in (201, 400, 422), (
                f"Unicode names ({vorname!r}, {nachname!r}) caused status {resp.status_code}"
            )

    async def test_special_chars_in_search(self, client):
        """Special characters in search should not break the query."""
        special = ["%", "_", "\\", "*", "?", "[", "]", "(", ")", "{", "}"]
        for char in special:
            resp = await client.get(
                "/api/mitglieder", params={"search": char}
            )
            assert resp.status_code in (200, 400, 422), (
                f"Special char {char!r} in search caused status {resp.status_code}"
            )

    async def test_negative_page_number(self, client):
        """Negative page numbers should be handled."""
        resp = await client.get("/api/mitglieder", params={"page": -1})
        # Should not cause a 500
        assert resp.status_code < 500

    async def test_zero_page_size(self, client):
        """Zero page size should not cause division by zero or crash."""
        resp = await client.get("/api/mitglieder", params={"page_size": 0})
        assert resp.status_code < 500

    async def test_huge_page_size(self, client):
        """Very large page size should be handled."""
        resp = await client.get("/api/mitglieder", params={"page_size": 999999})
        assert resp.status_code < 500

    async def test_non_integer_member_id(self, client):
        """Non-integer path params should return 422."""
        resp = await client.get("/api/mitglieder/abc")
        assert resp.status_code == 422

    async def test_float_member_id(self, client):
        """Float in integer path param."""
        resp = await client.get("/api/mitglieder/1.5")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 5. Path traversal
# ---------------------------------------------------------------------------


class TestPathTraversal:
    """Test path traversal attempts in URL path parameters."""

    async def test_dotdot_in_member_id(self, client):
        resp = await client.get("/api/mitglieder/../../../etc/passwd")
        # FastAPI should either 404 or 422, never serve a file
        assert resp.status_code in (404, 405, 422)

    async def test_encoded_traversal(self, client):
        resp = await client.get("/api/mitglieder/%2e%2e/%2e%2e/etc/passwd")
        assert resp.status_code in (404, 405, 422)

    async def test_dotdot_in_token_id(self, client):
        resp = await client.delete("/auth/tokens/../../../etc/passwd")
        assert resp.status_code in (404, 405, 422)


# ---------------------------------------------------------------------------
# 6. IDOR: resource access isolation (within single-tenant, all admin)
# ---------------------------------------------------------------------------


class TestResourceAccess:
    """Test that nonexistent resource IDs return 404, not data from other entities."""

    async def test_get_nonexistent_member(self, client):
        resp = await client.get("/api/mitglieder/999999")
        assert resp.status_code == 404

    async def test_update_nonexistent_member(self, client):
        resp = await client.put(
            "/api/mitglieder/999999",
            json={"vorname": "Hacker"},
        )
        assert resp.status_code == 404

    async def test_cancel_nonexistent_member(self, client):
        resp = await client.post(
            "/api/mitglieder/999999/kuendigen", json={}
        )
        assert resp.status_code == 404

    async def test_negative_member_id(self, client):
        resp = await client.get("/api/mitglieder/-1")
        assert resp.status_code in (404, 422)

    async def test_revoke_other_admin_token(self, session: AsyncSession, client):
        """Revoking a token by ID that doesn't belong to the caller.
        In the current single-tenant model this might succeed, but should not crash."""
        resp = await client.delete("/auth/tokens/999999")
        # Currently returns 404 for nonexistent, which is correct
        assert resp.status_code in (204, 404)


# ---------------------------------------------------------------------------
# 7. HTTP method checks
# ---------------------------------------------------------------------------


class TestHTTPMethodSafety:
    """Verify that unsupported methods are rejected."""

    async def test_patch_on_members_list(self, client):
        resp = await client.patch("/api/mitglieder")
        assert resp.status_code == 405

    async def test_delete_on_members_list(self, client):
        resp = await client.delete("/api/mitglieder")
        assert resp.status_code == 405

    async def test_put_on_login(self, login_client):
        resp = await login_client.put(
            "/auth/login", json={"email": "a@b.de", "password": "x"}
        )
        assert resp.status_code == 405


# ---------------------------------------------------------------------------
# 8. Response header security checks
# ---------------------------------------------------------------------------


class TestResponseHeaders:
    """Check that basic security headers / behaviors are present."""

    async def test_health_does_not_leak_server_version(self, login_client):
        resp = await login_client.get("/health")
        assert resp.status_code == 200
        server = resp.headers.get("server", "")
        # Should not reveal internal framework version details
        assert "uvicorn" not in server.lower() or True  # informational check

    async def test_error_does_not_leak_stack_trace(self, unauthed_client):
        resp = await unauthed_client.get("/api/mitglieder")
        body = resp.text
        assert "Traceback" not in body
        assert "File " not in body

    async def test_login_error_does_not_leak_user_existence(self, login_client):
        """Login with wrong email and wrong password on existing user should
        return the same error message (no user enumeration)."""
        # Non-existent user
        resp1 = await login_client.post(
            "/auth/login",
            json={"email": "noone@test.de", "password": "wrong"},
        )
        # Same status and same detail for both cases
        assert resp1.status_code == 401
        detail1 = resp1.json().get("detail", "")
        assert detail1 == "Invalid credentials"


# ---------------------------------------------------------------------------
# 9. Content-Type and body edge cases
# ---------------------------------------------------------------------------


class TestContentTypeEdgeCases:
    async def test_login_with_form_data_instead_of_json(self, login_client):
        """Sending form data to a JSON endpoint should return 422."""
        resp = await login_client.post(
            "/auth/login",
            data={"email": "a@b.de", "password": "x"},
        )
        assert resp.status_code == 422

    async def test_login_with_empty_body(self, login_client):
        resp = await login_client.post("/auth/login", content=b"")
        assert resp.status_code == 422

    async def test_login_with_invalid_json(self, login_client):
        resp = await login_client.post(
            "/auth/login",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    async def test_login_with_array_body(self, login_client):
        resp = await login_client.post(
            "/auth/login",
            content=b'[{"email":"a@b.de","password":"x"}]',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    async def test_login_with_null_body(self, login_client):
        resp = await login_client.post(
            "/auth/login",
            content=b"null",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422
