# EventAtlas

EventAtlas is a responsive discovery and management platform for exhibitions, trade shows, conferences, workshops, and business events.

## Stack
- React, React Router, CSS, Lucide icons, Sonner toasts
- FastAPI REST API with JWT authentication
- MongoDB with indexes for status/date, featured/date, and user email

The supplied workspace runs FastAPI/MongoDB, so the requested REST and JWT behavior is implemented on that existing service rather than introducing a second runtime the environment does not provide.

## Run locally
1. Keep the existing protected backend and frontend environment values.
2. Start the backend through the existing supervisor service on port 8001.
3. In `frontend`, run `yarn start`.
4. Open the configured frontend URL.

## Demo access
- Email: `admin@eventatlas.com`
- Password: `admin123`

The backend seeds this admin and five realistic events on first startup. Event image files are not stored in MongoDB; each event stores an external image URL.

## API
- `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
- `GET /api/events` with `search`, `category`, `industry`, `status`, `sort`, `page`, and `limit`
- `GET /api/events/featured`, `GET /api/events/{id}`, `GET /api/meta`
- Admin-only `POST`, `PUT`, and `DELETE /api/events` routes

## Architecture and scale notes
Events use stable UUID strings, ISO dates, projected responses without MongoDB `_id`, and indexed status/date and featured/date queries. For a 1M+ event catalog, the next step would be Atlas Search, cursor pagination, a CDN for image URLs, Redis caching for featured/meta responses, and read replicas behind the API.

## Known limitations
This MVP uses URL-based images and a single seeded admin. It does not yet include organizer self-service accounts, image upload/storage, attendee registration, or email notifications.