"""
Simple HTTP server for Render health checks.
Runs alongside the Discord bot to satisfy Render's web service requirements.
"""

import asyncio
import logging
from aiohttp import web
import os


async def health_check(request):
    """Health check endpoint for Render."""
    return web.Response(text="Bot is running!", status=200)


async def create_app():
    """Create the web application."""
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    return app


async def run_health_server():
    """Run the health check server."""
    logger = logging.getLogger(__name__)

    app = await create_app()
    port = int(os.environ.get("PORT", 10000))

    logger.info(f"Starting health server on port {port}")

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info(f"Health server running on http://0.0.0.0:{port}")

    # Keep the server running
    try:
        while True:
            await asyncio.sleep(3600)  # Sleep for 1 hour, then check again
    except asyncio.CancelledError:
        logger.info("Health server shutting down...")
        await runner.cleanup()
