from typing import Type, Dict, Any, Optional, Tuple

_registry_instance = None

def get_registry():
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ServiceContainers()
    return _registry_instance

class ServiceContainers:
    def __init__(self):
        if not hasattr(self, '_services'):
            self._services: Dict[Tuple[Type, Optional[str]], Any] = {}

    def register(self, service_type: Type, instance: Any, qualifier: Optional[str] = None):
        key = (service_type, qualifier)
        self._services[key] = instance

    def resolve(self, service_type: Type, qualifier: Optional[str] = None) -> Any:
        key = (service_type, qualifier)
        if key not in self._services:
            raise ValueError(f"Service not found for {service_type} with qualifier={qualifier}")
        return self._services[key]