# Ozhzo Verse — Authentication Specification

## 1. Overview
The Ozhzo Verse authentication system provides a unified, highly secure, mobile-first identity foundation with Argon2id password hashing, JWT stateless access tokens with cryptographic JTI rotation, and modular OTP verification.

## 2. Core Principles
- **Primary Identity**: Mobile Number (normalized in E.164 format with Country Code).
- **Secondary Identity**: Email Address (RFC 5322 compliant).
- **Credential Storage**: Argon2id password hashing with custom salt and memory-hardness.
- **Session Management**: Dual-token architecture (Access Token: 60 minutes, Refresh Token: 30 days) with Redis JTI blacklisting for instant logout revocation.

## 3. Endpoints & Flows
### `POST /api/v1/auth/send-otp`
Dispatches a 6-digit OTP verification code via the abstracted `OTPProvider` (Development vs. Production SMS/WhatsApp).
- **Rate Limit**: Max 5 requests/minute per phone number.
- **Expiry**: 10 minutes from dispatch.

### `POST /api/v1/auth/verify-otp`
Verifies user-supplied OTP against the stored SHA-256 hash.
- **Lockout Protection**: Max 5 invalid attempts per challenge before requiring a new code.
- Automatically marks `mobile_verified = true` upon success.

### `POST /api/v1/auth/register`
Creates a new user record.
- Normalizes phone number and enforces uniqueness across the tenant database.
- Issues JWT token pair immediately.

### `POST /api/v1/auth/login`
Authenticates via:
1. `phone_number` + `password`
2. `email` + `password`
3. `phone_number` + `otp_code`

### `POST /api/v1/auth/refresh`
Rotates access and refresh tokens. Blacklists old refresh token JTI in Redis.

### `POST /api/v1/auth/logout`
Blacklists active access token JTI in Redis until token expiration.
