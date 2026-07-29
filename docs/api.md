# API Documentation

## Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh token

## Chat
- `GET /api/v1/chat/` - List chats
- `POST /api/v1/chat/` - Create chat
- `GET /api/v1/chat/{id}` - Get messages
- `POST /api/v1/chat/{id}` - Send message
- `POST /api/v1/chat/{id}/stream` - Stream response

## Drafting
- `GET /api/v1/drafting/types` - List draft types
- `GET /api/v1/drafting/templates/{type}` - Get template
- `POST /api/v1/drafting/generate` - Generate draft

## Health
- `GET /api/v1/health` - System health check
