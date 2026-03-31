# Auth Testing Notes

- Login endpoint: `/api/auth/login`
- Current session endpoint: `/api/auth/me`
- Preview credentials:
  - Owner: `owner@fieldquality.local` / `FieldQA123!`
  - Production Manager: `production.manager@fieldquality.local` / `FieldQA123!`
  - GM: `gm@fieldquality.local` / `FieldQA123!`

## Quick Validation

1. POST valid credentials to `/api/auth/login`
2. Confirm token and role come back successfully
3. Use the returned token on `/api/auth/me`
4. Validate role-based routing in the frontend:
   - Owner: overview, owner review, calibration, rapid review, exports, settings
   - Management: overview, alignment & QR, review queue, rapid review, settings
5. Confirm login screen remembers the last successful role preset without altering the branded start-screen theme