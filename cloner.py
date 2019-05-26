import argparse
import json

from queue import Queue


class Entity:
    """ Represents an entity and stores links to other entities in `children`
    """

    def __init__(self, entity_id, name, description=None, children=set()):
        self.entity_id = entity_id
        self.name = name
        self.description = description
        self.children = set(children)

    def __eq__(self, other):
        return isinstance(other, Entity) \
            and self.entity_id == other.entity_id \
            and self.name == other.name \
            and self.description == other.description

    def __hash__(self):
        return hash((self.entity_id, self.name, self.description))

    def to_dict(self):
        result = {
            'entity_id': self.entity_id,
            'name': self.name,
        }
        if self.description:
            result['description'] = self.description

        return result

    def __repr__(self):
        children = ['(%s, %s)' % (c.entity_id, c.name) for c in self.children]
        return '(%s, %s) -> %s' % (self.entity_id, self.name, children)


class EntityGraph:
    """ Represents a graph of `Entity` objects.

        Stores id of entity from which the cloning will begin in `start`.

        Stores parents of start entity which are later used to restore
        the links to cloned start entity.
    """
    def __init__(self, start):
        self.start = start
        self.entities = {}
        self.start_parents = set()

    def add_entity(self, entity_id, name, description=None):
        """ Add entity to `entities` dict """
        if entity_id in self.entities:
            raise ValueError('Entity with id: %s already present' % entity_id)
        entity = Entity(entity_id, name, description)
        self.entities[entity_id] = entity

    def add_link(self, from_entity, to_entity):
        """ Add link between entities. Entity with id `from_entity` will
            become parent of entity with id `to_entity` adn have it
            in its `children`.

            Also, add `from_entity` to `start_parents` if
            `to_entity` id of start.
        """
        if from_entity not in self.entities:
            raise LookupError('There is no entity with id: %s' % from_entity)
        if to_entity not in self.entities:
            raise LookupError('There is no entity with id: %s' % to_entity)

        entity = self.entities[from_entity]
        entity.children.add(self.entities[to_entity])
        if to_entity == self.start:
            self.start_parents.add(from_entity)

    def has_entity(self, entity_id):
        return entity_id in self.entities

    def get_entity(self, entity_id):
        return self.entities.get(entity_id)

    def get_start(self):
        return self.get_entity(self.start)

    @classmethod
    def build_from_data(cls, start, data):
        """ Build graph from json data """
        inst = cls(start)
        for entity in data['entities']:
            inst.add_entity(**entity)

        if start not in inst.entities:
            raise ValueError(
                'Entity with id %s is not in provided entities' % start
            )

        for link in data['links']:
            inst.add_link(link['from'], link['to'])

        return inst

    def to_dict(self):
        result = {
            'entities': [],
            'links': []
        }
        for entity in self.entities.values():
            result['entities'].append(entity.to_dict())
            for child in entity.children:
                result['links'].append({
                    'from': entity.entity_id,
                    'to': child.entity_id
                })

        return result

    def __repr__(self):
        return '\n'.join([repr(entity) for entity in self.entities.values()])


class EntityCloner:
    """ Clones subraph of given initial graph of entities and
        initial entity id (start).
    """
    def __init__(self, initial_graph):
        self.initial_graph = initial_graph
        self.cloned_graph = None
        self._current_id = 0

    def generate_id(self):
        """ Generate sequential integer id which is unique across
            initial and cloned graphs.
        """
        self._current_id += 1
        while self.initial_graph.has_entity(self._current_id) or \
                (self.cloned_graph and
                 self.cloned_graph.has_entity(self._current_id)):
            self._current_id += 1

        return self._current_id

    def clone_subgraph(self):
        """ Traverse initial graph starting from initial entity_id (start),
            clone all related entities and return the cloned subgraph.
        """
        current = self.initial_graph.get_start()
        cloned_start = self.generate_id()
        self.cloned_graph = EntityGraph(cloned_start)
        self.cloned_graph.add_entity(
            cloned_start, current.name, current.description
        )

        # maps initial graph's ids to cloned ids and marks visited entities
        visited = {}
        queue = Queue()
        visited[current.entity_id] = cloned_start
        queue.put(current)
        while not queue.empty():
            current = queue.get()
            for child in current.children:
                if child.entity_id not in visited:
                    # clone child and link it to parent
                    cloned_id = self.generate_id()
                    self.cloned_graph.add_entity(
                        cloned_id, child.name, child.description
                    )
                    self.cloned_graph.add_link(
                        visited[current.entity_id], cloned_id
                    )
                    queue.put(child)
                    visited[child.entity_id] = cloned_id
                else:
                    # child is already cloned, only link it to parent
                    self.cloned_graph.add_link(
                        visited[current.entity_id], visited[child.entity_id]
                    )

        return self.cloned_graph


def construct_output(initial, cloned):
    """ Construct desired output by:
        1. Combining initial and cloned graphs
        2. Adding links to cloned initial entity
    """
    initial_dict = initial.to_dict()
    cloned_dict = cloned.to_dict()
    start_parents = [{'from': parent, 'to': cloned.start}
                     for parent in initial.start_parents]
    return {
        'entities': initial_dict['entities'] + cloned_dict['entities'],
        'links': initial_dict['links'] + cloned_dict['links'] + start_parents
    }


def parse_arguments():
    parser = argparse.ArgumentParser('entity cloner')
    parser.add_argument(
        'filename',
        help='filename to json file with entities and links',
        type=str
    )
    parser.add_argument(
        'entity_id',
        help='id of the entity to clone',
        type=int
    )
    args = parser.parse_args()
    return args.filename, args.entity_id


def read_json_file(filename):
    try:
        with open(filename) as input_file:
            return json.load(input_file)
    except json.decoder.JSONDecodeError:
        print('Contents of %s is not a valid json' % filename)
        raise
    except FileNotFoundError:
        print('File %s does not exist' % filename)
        raise


if __name__ == '__main__':
    filename, entity_id = parse_arguments()
    data = read_json_file(filename)
    initial_graph = EntityGraph.build_from_data(start=entity_id, data=data)
    cloner = EntityCloner(initial_graph)
    cloned_graph = cloner.clone_subgraph()
    print(json.dumps(construct_output(initial_graph, cloned_graph), indent=4))
