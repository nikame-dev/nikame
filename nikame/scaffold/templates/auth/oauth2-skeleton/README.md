# OAuth2 Flow Skeleton

Provides a drop-in skeleton for handling external OAuth2 Single-Sign-On providers. Includes a canonical implementation for Google OAuth.

## Workflow

1. User visits `/auth/oauth2/login/google`
2. Endpoint issues an HTTP 307 Redirect to `https://accounts.google.com/...`
3. User signs in on Google
4. Google redirects user strictly back to `/auth/oauth2/callback/google?code=XYZ`
5. The callback endpoint receives the code, executes an explicit backend-to-backend HTTPS request to Google to exchange `code` -> `access_token`
6. The backend makes a second HTTPS request to Google to get user `email`
7. The backend writes this user to your database
8. The backend kicks out a native standard system JWT (`create_access_token`)

## Usage

Mount the new router in your application:

```python
from app.routers.oauth2 import router as oauth2_router

app.include_router(oauth2_router)
```

## Gotchas

* Requires Google Developer Console setup to get `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
* You *must* configure Google Developer Console to allow the exact Callback URL string matching `OAUTH_CALLBACK_URL` otherwise Google will reject step 2.
