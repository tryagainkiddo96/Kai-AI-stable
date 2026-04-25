"""
Cloud Kai Client - Connect local Kai to cloud server
For users with limited local resources (like 8GB RAM)
"""

import asyncio
import aiohttp
import json
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CloudKaiClient:
    """
    Client for connecting local Kai to cloud Kai Enterprise server.
    Enables offloading heavy tasks to cloud while keeping local responsiveness.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "C:\\Users\\7nujy6xc\\.kai\\cloud.json"
        self.config = self._load_config()
        self.session: Optional[aiohttp.ClientSession] = None
        # Override timeout for faster health checks
        self.config["timeout"] = 10  # 10 seconds max for health check

    def _load_config(self) -> Dict[str, Any]:
        """Load cloud configuration"""
        default_config = {
            "endpoint": "https://trapdoorkid.cybermods.com",
            "timeout": 300,
            "retry_attempts": 3,
            "compression": True,
            "verify_ssl": True,
            "api_key": None,
        }

        try:
            if self.config_path and os.path.exists(self.config_path):
                with open(self.config_path, "r") as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
        except Exception as e:
            logger.warning("Failed to load cloud config: {}".format(e))

        return default_config

    async def _ensure_session(self):
        """Ensure aiohttp session is available"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config["timeout"]),
                connector=aiohttp.TCPConnector(verify_ssl=self.config["verify_ssl"]),
            )

    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def health_check(self) -> Dict[str, Any]:
        """Check if cloud server is healthy"""
        await self._ensure_session()

        try:
            async with self.session.get(
                "{}/health".format(self.config["endpoint"])
            ) as response:
                if response.status == 200:
                    return {"status": "healthy"}
                else:
                    return {"status": "unhealthy", "status_code": response.status}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def should_offload_task(
        self, task_complexity: str, local_ram_gb: float = None
    ) -> bool:
        """
        Determine if a task should be offloaded to cloud

        Args:
            task_complexity: 'low', 'medium', 'high'
            local_ram_gb: Local system RAM (auto-detected if None)
        """
        if local_ram_gb is None:
            local_ram_gb = self._get_system_ram()

        # Offload thresholds based on local RAM
        thresholds = {
            4: {"low": False, "medium": True, "high": True},  # 4GB: offload medium+
            8: {"low": False, "medium": False, "high": True},  # 8GB: offload high only
            16: {"low": False, "medium": False, "high": False},  # 16GB+: keep local
        }

        # Find appropriate threshold
        applicable_threshold = 4  # Default conservative
        for ram_threshold in sorted(thresholds.keys()):
            if local_ram_gb >= ram_threshold:
                applicable_threshold = ram_threshold

        return thresholds[applicable_threshold].get(task_complexity, True)

    def _get_system_ram(self) -> float:
        """Get system RAM in GB"""
        try:
            import psutil

            return round(psutil.virtual_memory().total / (1024**3), 1)
        except ImportError:
            return 8.0  # Default assumption


# Global cloud client instance
_cloud_client = None


def get_cloud_client() -> CloudKaiClient:
    """Get or create global cloud client instance"""
    global _cloud_client
    if _cloud_client is None:
        _cloud_client = CloudKaiClient()
    return _cloud_client


async def init_cloud_support():
    """Initialize cloud support for Kai (non-blocking)"""
    client = get_cloud_client()

    try:
        # Test connection with short timeout
        health = await asyncio.wait_for(client.health_check(), timeout=10.0)
        if health.get("status") == "healthy":
            print("✅ Cloud Kai server connection established")
            print("   Server: {}".format(client.config["endpoint"]))
            print("   Local RAM: {}GB".format(client._get_system_ram()))
            return True
        else:
            print("⚠️  Cloud Kai server not available")
            return False
    except asyncio.TimeoutError:
        print("⚠️  Cloud Kai server timeout (continuing offline)")
        return False
    except Exception:
        print("⚠️  Cloud Kai server unavailable (continuing offline)")
        return False
