# Moduł auth — Specification

> Status: IMPLEMENTED (v0.1)
> depends_on: [base]

---

## Cel modułu

Autentykacja i autoryzacja użytkowników. JWT-based, stateless.
Obsługa: login, register, refresh token, multi-company org picker, TOTP 2FA.

---

## Flow autentykacji

### Standard login
```
POST /api/auth/login {email, password}
  → verify password (bcrypt)
  → check TOTP if enabled
  → if user has 1 company → issue tokens immediately
  → if user has N companies → return {requires_company_selection: true, companies: [...]}
      → POST /api/auth/select-company {company_id}
      → issue tokens
```

### Token structure (JWT payload)
```json
{
  "sub": "user-uuid",
  "tenant_id": "tenant-uuid",
  "company_id": "company-uuid",
  "roles": ["base.group_user", "crm.salesman"],
  "is_superadmin": false,
  "exp": 1234567890
}
```

### Token lifecycle
- `access_token` — 60 min, używany w każdym API request
- `refresh_token` — 30 days, używany tylko do odnowienia access_token
- Storage: localStorage w przeglądarce
- Interceptor 401 → redirect /login + clear localStorage

---

## Endpoints

### POST /api/auth/login
```
Request:  {email, password, totp_code?}
Response: {access_token, refresh_token, requires_totp?, requires_company_selection?, companies?}
Errors:   401 Invalid email or password
          401 Account disabled
          401 Invalid TOTP code
```

### POST /api/auth/register
Samodzielna rejestracja — tworzy nowego tenanta + pierwszego użytkownika (owner).
```
Request:  {name, email, password, tenant_name, tenant_slug}
Response: {access_token, refresh_token}
Errors:   400 Tenant slug already taken
```
Tworzy automatycznie:
1. Tenant
2. Company (o nazwie tenant_name)
3. User (is_superadmin=True, company_ids=[company.id])

### POST /api/auth/refresh
```
Request:  {refresh_token}
Response: {access_token, refresh_token}
Errors:   401 Invalid refresh token
```

### POST /api/auth/select-company
```
Request:  {company_id}  [requires auth — partial token z requires_company_selection]
Response: {access_token, refresh_token}
Errors:   403 Company not accessible
```

### GET /api/auth/me
```
Response: UserRead schema
Errors:   401
```

### POST /api/auth/totp/setup
```
Response: {secret, provisioning_uri}
```
Generuje secret TOTP. Użytkownik skanuje QR code w aplikacji (Google Authenticator itp.).
Secret jest zapisany ale TOTP nie jest jeszcze włączone.

### POST /api/auth/totp/verify
```
Request:  {code}
Response: {message: "2FA enabled successfully"}
Errors:   400 TOTP not set up
          400 Invalid TOTP code
```
Potwierdza kod i ustawia totp_enabled=True.

---

## Security

- Hasła: bcrypt (cost factor 12)
- JWT: HS256, secret z settings.secret_key
- TOTP: RFC 6238 (30-second window)
- Brak możliwości logowania gdy is_active=False

---

## TODO

| Feature | Priority | Uwagi |
|---|---|---|
| Password reset flow | High | Email → token → new password |
| OAuth2 / SSO | Medium | Google, Microsoft |
| Session management | Medium | Revoke refresh tokens, list active sessions |
| Rate limiting login | High | Brute force protection |
| Audit log login attempts | Medium | |
