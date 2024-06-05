# Flexible Light-Weight Object-Oriented ECS [ inspired by esper ]

import time as _time
from typing import Callable as _Callable
from typing import Dict as _Dict
from typing import List as _List
from typing import Any as _Any
from typing import Set as _Set
from typing import Type as _Type
from typing import Tuple as _Tuple
from typing import Iterable as _Iterable
from typing import Optional as _Optional
from typing import overload as _overload
from itertools import count as _count
from collections import defaultdict
from typing import TypeVar as _TypeVar

from .version import *

_Scene = _TypeVar('_Scene')  # custom typing
_Component = _TypeVar('_Component')  # custom typing
_Processor = _TypeVar('_Processor')  # custom typing

class Processor:
    """Base class for all Processors to inherit from.

    Processor instances must contain a `process` method, otherwise 
    feel free to define the class any way you'd like. 

    Processors should be instantiated, and then added to the current scene context by calling :py:func:`swarm.Processor.register`.

    For example::

        my_processor_instance = MyProcessor()
        my_processor_instance.register(my_processor_instance)

     All the Processors that have been added to the scene context will have their
    :py:meth:`swarm.Processor.process` methods called by a single call to :py:meth:`swarm.Scene.process`.

    Inside the `process` method is generally where you
    should iterate over Entities with one (or more) calls to the appropriate methods::

        def process(self):
            for ent, (rend, vel) in swarm.get_components(Renderable, Velocity):
                your_code_here()
    """
    def __init__(self) -> None:
        self.priority: int = 0

    @staticmethod
    def process(*args: _Any, **kwargs: _Any) -> None:
        raise NotImplementedError

class Scene:
    def __init__(self) -> None:
        self._dead_entities: _Set[int] = set()
        self.entity_count: "_count[int]" = _count(start=0)
        self.entities: _Dict[int, _Dict[_Type[_Component], _Component]] = {}

        self.components: _Dict[_Component, _Set[int]] = {}
        self.components_typed: _Dict[_Type, _Set[_Component]] = {}
        self.component_cache:_Dict[_Tuple[int, _Type[_Component]], _Component] = {}

        self.process_times: _Dict[str, int] = {}
        self.event_registry: _Dict[str, _Any] = {}
        self.processors: _Dict[_Type[_Processor], _Processor] = {}

    def clear_scene(self) -> None:
        """Clear the Scene.

        Removes all Entities and Components from the current scene.
        Processors are not removed.
        """
        self.entities.clear()
        self.components.clear()
        self._dead_entities.clear()
        self.entity_count = _count(start=1)

    def fetch_processor(self, p_type):
        """Fetch a Processor instance, by type.

        This function returns a Processor instance by type. This could be
        useful in certain situations, such as wanting to call a method on a
        Processor, from within another Processor.
        """
        for p in self.processors:
            if type(p) is p_type:
                return p
        else:
            return None

    def register_processor(self, processor, priority: int = 0):
        """Register a Processor by instance or type to the current scene.

        Add a Processor instance to the scene (subclass of
        :py:class:`swarm.Processor`), with optional priority.

        When the :py:func:`swarm.Scene.process` function is called,
        Processors with higher priority will be called first.
        """

        if isinstance(processor, type):
            instance = processor()
        else:
            instance = processor

        instance.scene = self

        if type(instance) not in self.processors:
            if priority:
                instance.priority = priority
            self.processors[type(instance)] = instance

    def unregister_processor(self, p_type):
        """Remove a Processor from the scene, by type.

        Make sure to provide the class itself, **not** an instance. For example::

            # OK:
            self.scene.remove_processor(MyProcessor)

            # NG:
            self.scene.remove_processor(my_processor_instance)

        """
        if p_type not in self.processors:
            print("\nprocessor not registered")
            return
        del self.processors[p_type]

    def make_entity(self, *components: _Component) -> int:
        """Create a new Entity, with optional initial Components.

        This funcion returns an Entity ID, which is a plain integer.
        You can optionally pass one or more Component instances to be
        assigned to the Entity on creation. Components can be also be
        added later with the :py:func:`swarm.Component.add` funcion.
        """
        entity = next(self.entity_count)

        if entity not in self.entities:
            self.entities[entity] = {}

        for c_instance in components:
            c_type = type(c_instance)
            if c_type not in self.components:
                self.components[c_type] = c_instance
        return entity

    def kill_entity(self, entity: int, instant: bool = False) -> None:
        """Delete an Entity from the current scene.

        Delete an Entity and all of it's assigned Component instances from
        the scene. By default, Entity deletion is delayed until the next call
        to :py:meth:`swarm.Scene.process`. You can, however, request instant
        deletion by passing the `instant=True` parameter. Note that instant
        deletion may cause issues, such as when done during Entity iteration
        (calls to swarm.Component.get/fetch/set/s).

        Raises a KeyError if the given entity does not exist in the database.
        """
        if instant:
            for c_type in self.entities[entity]:
                self.components[c_type].discard(entity)

                if not self.components[c_type]:
                    del self.components[c_type]

            del self.entities[entity]
        else:
            self._dead_entities.add(entity)

    def is_entity(self, entity: int) -> bool:
        """Check if a specific Entity exists.

        Bare Entities (with no components) and dead Entities (killed
        by kill_entity) will not count.
        """
        return entity in self.entities and entity not in self._dead_entities

    def _destroy_entities(self):
        """Finalize deletion of any Entities that are marked as dead.

        This function is provided for those who are not making use of
        :py:meth:`swarm.Scene.register_processor` and :py:meth:`swarm.Scene.process`. 
        
        If you are calling your processors manually, this function should be called in
        your main loop after calling all processors.
        
        Performs deletion in batches to minimize impact.
        """
        to_delete = []
        for entity in self._dead_entities:
            to_delete.append(entity)

        for entity in to_delete:
            self._delete_entity(entity)
            
        self._dead_entities.clear()

    def __destroy_all(self) -> None:
        """This function iterates over every
        entity within :py:meth:`swarm.Scene._dead_entities` making sure each one is deleted.
        It is advised to use :py:meth:`swarm.Scene._destroy_entities` for the deletion of entities.
        """
        for entity in self._dead_entities:

            for c_type in self.entities[entity]:
                self.components[c_type].discard(entity)

                if not self.components[c_type]:
                    del self.components[c_type]

            del self.entities[entity]

        self._dead_entities.clear()

    def try_component(self, entity: int, c_type: _Type[_Component]) -> _Optional[_Component]:
        """Try to get a single component type for an Entity.

        This function will return the requested Component if it exists,
        or None if it does not. This allows a way to access optional Components
        that may or may not exist, without having to first query if the Entity
        has the Component type.
        """
        if c_type in self.entities[entity]:
            return self.entities[entity][c_type]
        return None

    def try_components(self, entity: int, *component_types: _Type[_Component]) -> _Optional[_Tuple[_Component, ...]]:
        """Try to get a multiple component types for an Entity.

        This function will return the requested Components if they exist,
        or None if they do not. This allows a way to access optional Components
        that may or may not exist, without first having to query if the Entity
        has the Component types.
        """
        if all(comp_type in self.entities[entity] for comp_type in component_types):
            # type: ignore[return-value]
            return [self.entities[entity][comp_type] for comp_type in component_types]
        return None

    def has_component(self, entity: int, c_type: _Type[_Component]) -> bool:
        """Check if an Entity has a specific Component type."""
        return c_type in self.entities[entity]

    def has_components(self, entity: int, *component_types: _Type[_Component]) -> bool:
        """Check if an Entity has all the specified Component types."""
        return all(comp_type in self.entities[entity] for comp_type in component_types)

    def fetch_component(self, entity: int, c_type: _Type[_Component]) -> _Component:
        """Retrieve a component instance for a given entity.
        In some cases direct access/modification of components is necessary,
        such as modifying values based on user input.

        Raises a KeyError if the component type does not exist for the entity.
        """
        if (entity, c_type) in self.component_cache:
            return self.component_cache[(entity, c_type)]
        component = self.entities[entity][c_type]
        self.component_cache[(entity, c_type)] = component
        return component

    def _fetch_all(self, entity: int) -> _Tuple[_Component, ...]:
        """Retrieve all Components for a specific Entity, as a Tuple.

        Retrieve all Components for a specific Entity. This function is probably
        not appropriate to use in your Processors, but might be useful for
        saving state, or passing specific Components between Scene contexts.
        Unlike most other functions, this returns all the Components as a
        Tuple in one batch, instead of returning a Generator for iteration.

        Raises a KeyError if the given entity does not exist in the database.
        """
        return tuple(self.entities[entity].values())

    def fetch_entities(self, c_type: _Type[_Component]):
        """Fetch all the entities associated with a component.
        
        Extremely useful for iteration on components in processors, 
        allowing you to target specific entity groups rather than iterating over all entities.
        
        Returns a set of all entities associated with the given component type or an empty set if the component type is not found.
        """
        try:
            return self.components[c_type]
        except(KeyError) as err:
            # print(f"[swarm] :: ERROR :: fetch_entities() :: C_TYPE[{c_type}] NOT FOUND")
            return set()

    def fetch_all_type(self, c_type: _Type[_Component]):
        """Fetch all component instances by type.
        
        Extremely useful for iteration on components in processors, 
        allowing you to skip iteration and manipulate components directly.
        
        Returns a set of all instances of the given component type.
        """
        return self.components_typed[c_type]

    def add_component(self, *args, entity: int, component: _Component, type_alias: _Optional[_Type[_Component]] = None, **kwargs) -> None:
        """Add a new Component to an Entity.

        Add a Component to an Entity by type. If a Component of the same type
        is already assigned to the Entity, it will be replaced.

        A `type_alias` can also be provided. This can be useful if you're using
        subclasses to organize your Components, but would like to query them
        later by some common parent type.
        """
        comp = component(*args, **kwargs)
        
        c_type = type_alias or type(comp)
        if c_type not in self.components:
            self.components[c_type] = set()
            if c_type not in self.components_typed:
                self.components_typed[c_type] = set()

        self.components[c_type].add(entity)
        self.components_typed[c_type].add(comp)

        self.entities[entity][c_type] = comp

    def remove_component(self, entity: int, c_type: _Type[_Component]) -> _Component:
        """Remove a Component instance from an Entity, by type.

        A Component instance can only be removed by providing its type.
        For example: swarm.delete_component(enemy_a, Velocity) will remove
        the Velocity instance from the Entity enemy_a.

        Raises a KeyError if either the given entity or Component type does
        not exist in the database.
        """
        self.components[c_type].discard(entity)

        if not self.components[c_type]:
            del self.components[c_type]

        return self.entities[entity].pop(c_type)

    def process(self, *args: _Any, **kwargs: _Any) -> None:
        """Call the process method on all Processors, in order of their priority.

        Call the :py:meth:`swarm.Processor.process` method on all assigned
        Processors, respective of their priority. In addition, any Entities
        that were marked for deletion since the last call will be deleted
        at the start of this call.
        """
        self.component_cache.clear()
        self._destroy_entities()
        for processor in self.processors: # remember to sort by prority and then process
            processor.process(*args, self, **kwargs)

    def timed_process(self, *args: _Any, **kwargs: _Any) -> None:
        """Track Processor execution time for benchmarking.

        This function is identical to :py:meth:`swarm.Scene.process`, but
        it additionally records the elapsed time of each processor
        call (in milliseconds/ms) in the`swarm.process_times` dictionary.
        """
        self.component_cache.clear()
        self.destroy_entities()
        self.process_times.setdefault('historical', defaultdict(list))
        for processor in self.processors:
            start_time = _time.process_time()
            processor.process(*args, self, **kwargs)
            elapsed_time = int((_time.process_time() - start_time) * 1000)
            self.process_times[processor.__class__.__name__] = elapsed_time
            self.process_times['historical'][processor.__class__.__name__].append(elapsed_time)



# SCENE MANAGEMENT
_current_scene: str = "default"
SCENES: _Dict[str, Scene] = {"default": Scene()}

def new_scene(scene_name:str):
    if scene_name in SCENES:
        print(f"SCENE :: {scene_name} :: EXISTS :: ATTEMPTING OVERWRITE\n")
    SCENES[scene_name] = Scene()
    _current_scene = scene_name

def rem_scene(scene_name:str):
    try:
        SCENES.pop(scene_name)
        scenes:list[str] = list(SCENES.keys())
        if _current_scene == scene_name:
            _current_scene = scenes[len(scenes)-1]
    except(KeyError) as err:
        print(f"SCENE :: {scene_name} :: NOT FOUND :: {err}\n")
        
def reset_scene(scene_name:str):
    if scene_name in SCENES:
        SCENES[scene_name] = Scene()

def get_scene(scene_name:str):
    if scene_name in SCENES:
        return SCENES[scene_name]

def set_scene(scene_name:str):
    if scene_name in SCENES:
        _current_scene = scene_name

print(f"swarm {SWARM_MAJOR_VER}.{SWARM_MINOR_VER}.{SWARM_PATCH_VER}+{SWARM_YR_EDITION}")
