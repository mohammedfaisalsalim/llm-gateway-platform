def get_router():
    """Lazy load routing components to maintain safe initialization sequences."""
    from app.routes.chat import router
    return router