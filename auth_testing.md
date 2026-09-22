# Auth testing playbook

1. POST `/api/auth/login` with `admin@eventatlas.com` / `admin123`.
2. Confirm a secure `access_token` cookie is returned.
3. GET `/api/auth/me` with that cookie and confirm the admin role.
4. Confirm unauthenticated event mutation requests return 401/403.
5. Confirm the admin can create, update, and delete events.