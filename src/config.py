import os

class Config:
    def __init__(self):
        self.url = os.getenv("GAME_URL", "http://localhost:8080/game")
        self.max_iterations = int(os.getenv("MAX_ITERATIONS", 20))
        self.timeout_seconds = int(os.getenv("TIMEOUT_SECONDS", 20))
        self.driver_type = os.getenv("DRIVER_TYPE", "Chrome")
