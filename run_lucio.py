import threading
import time

import uvicorn

from backend.src.listener import main as listener_main


def start_backend() -> None:
    config = uvicorn.Config(
        "backend.src.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info",
    )
    server = uvicorn.Server(config)
    server.run()


def start_listener() -> None:
    listener_main()


def main() -> None:
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()

    time.sleep(1.0)

    print("Lucio backend started on http://127.0.0.1:8000")
    print("Starting voice listener...")

    start_listener()


if __name__ == "__main__":
    main()

