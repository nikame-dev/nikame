import socket


class ResourceResolver:
    """Resolves infrastructure resources like available ports and database indexes."""

    @staticmethod
    def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
        """Checks if a port is currently in use on the host."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((host, port)) == 0

    @staticmethod
    def find_available_port(start_port: int, exclude: set[int] | None = None) -> int:
        """Finds the first available port starting from start_port."""
        exclude = exclude or set()
        port = start_port
        while port <= 65535:
            if port not in exclude and not ResourceResolver.is_port_in_use(port):
                return port
            port += 1
        raise RuntimeError(f"Could not find an available port starting from {start_port}")

    @staticmethod
    def resolve_redis_db(allocated_dbs: set[int]) -> int:
        """Allocates a Redis database index (0-15) not in the allocated set."""
        for db in range(16):
            if db not in allocated_dbs:
                return db
        raise RuntimeError("No available Redis database indexes (0-15).")
