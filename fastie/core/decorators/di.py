import inspect
import logging
from abc import ABC
from functools import wraps
from typing import Type, Optional, Any, Dict, Set, get_type_hints

from fastie.core.service_containers.service_containers import get_registry

logger = logging.getLogger(__name__)

_component_registry = {}
_initialized_components = {}
_processing_stack = set()
_interface_implementations = {}

class Scope:
    SINGLETON = "singleton"
    PROTOTYPE = "prototype"

def component(cls=None, *, scope: str = Scope.SINGLETON, qualifier: Optional[str] = None, lazy: bool = True):
    def decorator(cls):
        _component_registry[cls] = {
            'scope': scope,
            'qualifier': qualifier,
            'lazy': lazy
        }

        # Register implementation for all interfaces in the class hierarchy
        def register_for_interfaces(base_cls):
            if base_cls == object or base_cls == ABC:
                return

            # Register this implementation for the current interface
            key = (base_cls, qualifier)
            _interface_implementations[key] = cls

            # Register for parent interfaces too
            for parent in base_cls.__bases__:
                register_for_interfaces(parent)

        # Start with direct bases
        for base in cls.__bases__:
            register_for_interfaces(base)

        return cls

    if cls is None:
        return decorator
    return decorator(cls)

def infrastructure(cls=None, *, qualifier: Optional[str] = None):
    return component(cls, scope=Scope.SINGLETON, qualifier=qualifier, lazy=False)

def component_decorator(cls=None, *, qualifier: Optional[str] = None):
    """
    Component decorator with same priority as infrastructure.
    Components are eagerly loaded (lazy=False) and singleton scoped.

    Usage examples:
    @component_decorator
    class MyComponent:
        pass

    @component_eager  # Using alias
    class AnotherComponent:
        pass

    @component_decorator(qualifier="special")
    class SpecialComponent:
        pass
    """
    return component(cls, scope=Scope.SINGLETON, qualifier=qualifier, lazy=False)

# Alias for easier usage
component_eager = component_decorator

def service(cls=None, *, scope: str = Scope.SINGLETON, qualifier: Optional[str] = None, lazy: bool = True):
    return component(cls, scope=scope, qualifier=qualifier, lazy=lazy)

def repository(cls=None, *, scope: str = Scope.SINGLETON, qualifier: Optional[str] = None, lazy: bool = True):
    return component(cls, scope=scope, qualifier=qualifier, lazy=lazy)

def controller(cls=None, *, qualifier: Optional[str] = None):
    return component(cls, scope=Scope.SINGLETON, qualifier=qualifier, lazy=True)

def _initialize_component(cls):
    if cls in _processing_stack:
        raise RuntimeError(f"Circular dependency detected while initializing {cls.__name__}")
    if cls in _initialized_components:
        return _initialized_components[cls]

    config = _component_registry.get(cls, {'scope': Scope.SINGLETON})
    scope = config.get('scope', Scope.SINGLETON)
    qualifier = config.get('qualifier')

    _processing_stack.add(cls)

    constructor = cls.__init__
    type_hints = get_type_hints(constructor)
    params = {}

    for name, param_type in list(type_hints.items()):
        if name == 'return' or name == 'self':
            continue
        try:
            # Try to find implementation for the exact type
            key = (param_type, None)
            impl_cls = _interface_implementations.get(key)

            if not impl_cls:
                # Try with qualifier
                key = (param_type, qualifier)
                impl_cls = _interface_implementations.get(key)

                # If still not found, check if any registered implementation
                # is a subclass of the requested interface
                found_impls = []
                for (iface, qual), implementation in _interface_implementations.items():
                    if issubclass(iface, param_type) and (qual == qualifier or qual is None):
                        found_impls.append(implementation)
                
                if len(found_impls) > 1:
                    # If multiple implementations found and no qualifier, it's ambiguous
                    if not qualifier:
                        impl_names = [impl.__name__ for impl in found_impls]
                        logger.warning(f"Multiple implementations found for {param_type.__name__}: {impl_names}. Using {found_impls[0].__name__}")
                    impl_cls = found_impls[0]
                elif len(found_impls) == 1:
                    impl_cls = found_impls[0]

            if impl_cls:
                params[name] = _initialize_component(impl_cls)
            else:
                # Try resolve from registry
                registry = get_registry()
                params[name] = registry.resolve(param_type)
        except Exception as e:
            raise ValueError(f"Failed to resolve dependency '{name}: {param_type}' for {cls.__name__}: {e}")

    instance = cls(**params)
    _processing_stack.remove(cls)

    if scope == Scope.SINGLETON:
        _initialized_components[cls] = instance

    # Register in the service container
    registry = get_registry()
    registry.register(cls, instance, qualifier)

    # Also register for base classes/interfaces
    for base in cls.__mro__[1:]:  # Skip the class itself
        if base is object or base is ABC:
            continue
        registry.register(base, instance, qualifier)

    return instance

def inject(cls=None):
    def decorator(cls):
        original_init = cls.__init__

        @wraps(original_init)
        def new_init(self, *args, **kwargs):
            signature = inspect.signature(original_init)
            type_hints = get_type_hints(original_init)
            injected_kwargs = {}

            for name, param in signature.parameters.items():
                if name == 'self':
                    continue

                # If the parameter is already in kwargs or args, don't inject it
                # Note: basic implementation, usually @inject is for auto-wiring singletons
                if name in kwargs:
                    continue
                
                param_type = type_hints.get(name)
                if not param_type:
                    if param.default != inspect.Parameter.empty:
                        continue
                    raise ValueError(f"Missing type hint for parameter '{name}' in class {cls.__name__}")

                try:
                    registry = get_registry()
                    dependency = registry.resolve(param_type)
                    injected_kwargs[name] = dependency
                except ValueError:
                    logger.error(f"Failed to inject {param_type.__name__} into {cls.__name__}")
                    raise

            # Merge injected dependencies with provided kwargs
            final_kwargs = {**injected_kwargs, **kwargs}
            
            # Set attributes for all final dependencies (both injected and provided)
            for name, dep in final_kwargs.items():
                if name in signature.parameters:
                    setattr(self, name, dep)

            original_init(self, *args, **final_kwargs)

        cls.__init__ = new_init
        return cls

    if cls is None:
        return decorator
    return decorator(cls)

def load_components():
    # Group components by type to avoid multiple iterations
    components_by_type = {
        'Infrastructure': [],
        'Component': [],
        'Repository': [],
        'Service': [],
        'Controller': []
    }

    # Categorize components
    for cls, meta in _component_registry.items():
        if cls.__name__.endswith('Controller'):
            components_by_type['Controller'].append(cls)
        elif any(base.__name__.endswith('Repository') for base in cls.__mro__):
            components_by_type['Repository'].append(cls)
        elif any(base.__name__.endswith('Service') for base in cls.__mro__):
            components_by_type['Service'].append(cls)
        elif not meta['lazy'] and any(base.__name__.endswith('Infrastructure') for base in cls.__mro__):
            components_by_type['Infrastructure'].append(cls)
        elif not meta['lazy']:
            # Components marked with component_decorator (eager loading)
            components_by_type['Component'].append(cls)

    # Initialize in the correct order (Component has same priority as Infrastructure)
    for component_type in ['Infrastructure', 'Component', 'Repository', 'Service', 'Controller']:
        for cls in components_by_type[component_type]:
            if component_type in ['Infrastructure', 'Component'] and _component_registry[cls]['lazy']:
                continue
            _initialize_component(cls)

    print("Registered components:")
    for cls in _component_registry:
        print("-", cls.__name__)
