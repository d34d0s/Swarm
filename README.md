# Swarm
![Swarm](https://img.shields.io/badge/Swarm-ECS-0?style=for-the-badge&logo=pypi&logoColor=turquoise&labelColor=black&color=turquoise&link=https%3A%2F%2Fpypi.org%2Fproject%2FSwarm-ECS%2F)
![PYPIVersion](https://img.shields.io/pypi/v/Swarm-ECS?style=for-the-badge&logoColor=turquoise&labelColor=black&color=turquoise)
![Downloads](https://img.shields.io/pypi/dm/Swarm-ECS?style=for-the-badge&logoColor=turquoise&labelColor=black&color=turquoise)
![PythonVersion](https://img.shields.io/pypi/pyversions/Swarm-ECS?style=for-the-badge&logoColor=turquoise&labelColor=black&color=turquoise)
<br>
<br>
A Flexible Light-Weight Object-Oriented ECS
<br>
<br>
Swarm is designed to allow for custom component/processor definitions, and registry.
<br>
With an API that feels natural to use you can structure various kinds of complex systems, from games to the engine itself.

# Installation
Swarm is available via github or the python package index [pypi].
Installation via pypi is rather simple. Open a command line or terminal, and run the following command `assuming you have Python installed`:
```cmd
pip install swarm-ecs
```
If you wish to clone the repository to take a furhter look into the source-code `assuming you have git installed`:
```cmd
git clone https://github.com/Zero-th/Swarm.git
```
---
Now with Swarm installed, lets take a look at an...
<br>

# Example
The first thing we do is either grab the default scene created on import or make one ourselves. 
<br>
For simplicity lets grab the default.

```python
import swarm

scene = swarm.get_scene("default")
# scene = swarm.new_scene("My Scene")
```

Swarm is written for all the OOP fans, so the scene object comes with neumerous methods for generation, and management of both entities and components.

Making an entity is as simple as...
```python
my_entity = scene.make_entity()
my_entity2 = scene.make_entity()

print(f"My Entity: {my_entity}\n")
print(f"My 2nd Entity: {my_entity2}\n")
```
To keep things light-weight on the memory side, entities are simple integer idetifiers (starting from zero), which are then mapped to a dictionary of components associated with the given entity. Printing out an entity will simply show you its ID or quite literally which number entity it is.

Swarm was inspired by esper-ecs, and thanks to python's dynamic type system components and processors are able to be user-defined.

Lets make a simple `TransformComponent`.
```python
class TransformComponent:
    __slots__ = ('x', 'y')
    def __init__(self, x:int|float, y:int|float) -> None:
        self.x:int|float = x
        self.y:int|float = y
```
Swarm caches components by type in a dictionary where the value is a set() of all the entities that have an instance attached to them. This  makes fetching components simple and effective.

Lets add our transform components, and notice you can still pass custom parameters to the `swarm.scene.add_component(*args, entity:int, component:swarm._Component, **kwargs)` method.

```python
scene.add_component(
    x=10, y=20,
    entity=my_entity, component=TransformComponent
)
scene.add_component(
    x=20, y=30,
    entity=my_entity2, component=TransformComponent
)
```

Now in a real-world-scenario these components would need to be `processed` and have their data read/manipulated.
Swarm allows you to define how your components are accessed and utilized.

( NOTE ) Assigning higher value priorities to processors causes them to be ran earlier

So lets create a processor that fetches all the entities that have a TransformComponent, and prints them out. The we will register our processor with `swarm.scene.register_processor(processor:swarm.Processor,  priority:int)`.
```python
class TransformProcessor(swarm.Processor):
    @staticmethod
    def process(*args, **kwargs):
        entities_with_transform:list[int] = scene.fetch_entities(TransformComponent)
        print(f"Entities With TransformComponent: {[e for e in entities_with_transform]}")

scene.register_processor(TransformProcessor)
```
Now in whatever fashion you may choose, simply call your scene's `process(*args, **kwargs)` method and enjoy.

```python
while True:
    scene.process()

```

There are methods for scene management included in the API, as well as a global storage dictionary for each scene located at `swarm.SCENES`.

We've already used one in the above example `swarm.get_scene(scene_name:str)`, but lets take a look at the rest.

```python
swarm.new_scene(scene_name:str) -> None:...
```
This function stores a new `swarm.Scene()` instance with the given scene_name as the key
```python
swarm.rem_scene(scene_name:str) -> None:...
```
This function removes a given scene from the global storage dictionary should the scene exist, if not this will `raise a KeyError`.
```python
swarm.reset_scene(scene_name:str) -> None:...
```
This function 'resets' a scene stored under the given scene_name by deleting and re-instantiating it.
```python
swarm.set_scene(scene_name:str) -> None:...
```
This function allows you to set the `swarm._current_scene` variable to the scene_name given should it exist.
The `swarm._current_scene` variable is used to track which of the stored `swarm.Scene()` instances is currently 'active' or 'selected'.