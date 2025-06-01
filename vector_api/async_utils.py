import sys

def run_async(coro):
    try:
        import asyncio
        if sys.version_info >= (3, 7):
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
                return loop.run_until_complete(coro)
            else:
                return asyncio.run(coro)
        else:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(coro)
    except Exception as e:
        raise e
