from fastapi.middleware.gzip import GZipMiddleware


def setup_compression(app):
    app.add_middleware(GZipMiddleware, minimum_size=1000)
