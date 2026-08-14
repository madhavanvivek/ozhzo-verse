# Ozhzo Verse — User Identity Model

## 1. Overview
User Identity in Ozhzo Verse separates authentication credentials (`users` table) from user profile attributes (`user_profiles` table), ensuring decoupled schema evolution and strict privacy isolation.

## 2. Schema Structure
```sql
users (
  id UUID PRIMARY KEY,
  phone_number VARCHAR(32) UNIQUE NULL,
  country_code VARCHAR(8) NULL,
  email VARCHAR(255) UNIQUE NULL,
  password_hash VARCHAR(255) NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  is_verified BOOLEAN DEFAULT FALSE,
  mobile_verified BOOLEAN DEFAULT FALSE,
  is_super_admin BOOLEAN DEFAULT FALSE,
  system_role VARCHAR(32) DEFAULT 'USER',
  created_at TIMESTAMP WITH TIME ZONE,
  updated_at TIMESTAMP WITH TIME ZONE
);

user_profiles (
  id UUID PRIMARY KEY,
  user_id UUID UNIQUE REFERENCES users(id),
  display_name VARCHAR(100) NOT NULL,
  phone_number VARCHAR(50) NULL,
  country_code VARCHAR(8) NULL,
  avatar_url TEXT NULL,
  timezone VARCHAR(50) DEFAULT 'UTC',
  preferred_language VARCHAR(10) DEFAULT 'en',
  created_at TIMESTAMP WITH TIME ZONE,
  updated_at TIMESTAMP WITH TIME ZONE
);
```

## 3. Phone Number Normalization
- All mobile numbers are converted to canonical **E.164 standard** format (`+[CountryCode][NationalNumber]`) before validation, storage, and OTP issuance.
- Strict deduplication ensures that an individual mobile number maps to exactly one verified user identity.
