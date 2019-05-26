import unittest
from cloner import Entity, EntityGraph, EntityCloner


class TestEntity(unittest.TestCase):
    def test_eq(self):
        entity1 = Entity(1, 'Name')
        entity2 = Entity(1, 'Name')
        entity3 = Entity(1, 'Name', 'Desc')
        entity4 = Entity(1, 'Name', 'Desc')
        entity5 = Entity(1, 'Different')

        self.assertEqual(entity1, entity2)
        self.assertEqual(entity3, entity4)
        self.assertNotEqual(entity1, entity3)
        self.assertNotEqual(entity1, entity5)

    def test_hash_returns_same_when_equal(self):
        entity1 = Entity(1, 'Name')
        entity2 = Entity(1, 'Name')
        self.assertEqual(hash(entity1), hash(entity2))

    def test_to_dict_no_description(self):
        entity = Entity(1, 'Name')
        self.assertEqual(entity.to_dict(), {'entity_id': 1, 'name': 'Name'})

    def test_to_dict_with_description(self):
        entity = Entity(1, 'Name', 'Desc')
        self.assertEqual(
            entity.to_dict(),
            {'entity_id': 1, 'name': 'Name', 'description': 'Desc'}
        )


class TestEntityGraph(unittest.TestCase):
    def test_add_entity(self):
        graph = EntityGraph(1)
        graph.add_entity(1, 'Name1')
        graph.add_entity(2, 'Name2', 'Desc')
        graph.add_entity(3, 'Name3')
        self.assertEqual(len(graph.entities), 3)
        self.assertEqual(graph.get_entity(1), Entity(1, 'Name1'))
        self.assertEqual(graph.get_entity(2), Entity(2, 'Name2', 'Desc'))
        self.assertEqual(graph.get_entity(3), Entity(3, 'Name3'))

    def test_add_link(self):
        graph = EntityGraph(1)
        entity1 = Entity(1, 'Name1')
        entity2 = Entity(2, 'Name2', 'Desc')
        entity3 = Entity(3, 'Name3')

        graph.add_entity(entity1.entity_id, entity1.name)
        graph.add_entity(entity2.entity_id, entity2.name, entity2.description)
        graph.add_entity(entity3.entity_id, entity3.name)
        graph.add_link(entity1.entity_id, entity2.entity_id)
        graph.add_link(entity1.entity_id, entity3.entity_id)
        graph.add_link(entity3.entity_id, entity2.entity_id)
        graph.add_link(entity2.entity_id, entity1.entity_id)
        graph.add_link(entity2.entity_id, entity3.entity_id)

        self.assertEqual(graph.get_entity(1).children, set([entity2, entity3]))
        self.assertEqual(graph.get_entity(3).children, set([entity2]))
        self.assertEqual(graph.get_entity(2).children, set([entity1, entity3]))

    def test_build_from_data(self):
        data = {
            'entities': [{
                'entity_id': 1,
                'name': 'EntityA',
            }, {
                'entity_id': 2,
                'name': 'EntityB',
            }, {
                'entity_id': 3,
                'name': 'EntityC',
                'description': 'More details about entity C',
            }],
            'links': [{
                'from': 1,
                'to': 2
            }, {
                'from': 2,
                'to': 3
            }, {
                'from': 3,
                'to': 1
            }]
        }

        def assert_equal_entity(entity, d_entity):
            self.assertEqual(entity.entity_id, d_entity.get('entity_id'))
            self.assertEqual(entity.name, d_entity.get('name'))
            self.assertEqual(entity.description, d_entity.get('description'))

        graph = EntityGraph.build_from_data(2, data)
        entity1 = graph.get_entity(1)
        entity2 = graph.get_entity(2)
        entity3 = graph.get_entity(3)

        # assert entities are added
        assert_equal_entity(entity1, data['entities'][0])
        assert_equal_entity(entity2, data['entities'][1])
        assert_equal_entity(entity3, data['entities'][2])

        # assert entities are linked
        self.assertEqual(entity1.children, set([entity2]))
        self.assertEqual(entity2.children, set([entity3]))
        self.assertEqual(entity3.children, set([entity1]))

    def test_to_dict(self):
        graph = EntityGraph(1)
        graph.add_entity(1, 'Name1')
        graph.add_entity(2, 'Name2')
        graph.add_entity(3, 'Name3', 'Desc')

        graph.add_link(1, 2)
        graph.add_link(1, 3)
        graph.add_link(2, 3)

        d = graph.to_dict()

        self.assertEqual(3, len(d['entities']))
        self.assertEqual(3, len(d['links']))
        for d_entity in d['entities']:
            entity = graph.get_entity(d_entity['entity_id'])
            self.assertEqual(entity.entity_id, d_entity['entity_id'])
            self.assertEqual(entity.name, d_entity['name'])
            self.assertEqual(entity.description, d_entity.get('description'))

        for d_link in d['links']:
            from_entity = graph.get_entity(d_link['from'])
            to_entity = graph.get_entity(d_link['to'])
            self.assertIn(to_entity, from_entity.children)


class TestEntityCloner(unittest.TestCase):
    def test_generate_id(self):
        initial_graph = EntityGraph(1)
        initial_graph.add_entity(1, 'Name1')
        initial_graph.add_entity(2, 'Name2')
        initial_graph.add_entity(3, 'Name3')
        initial_graph.add_entity(5, 'Name5')
        cloner = EntityCloner(initial_graph)

        self.assertEqual(4, cloner.generate_id())
        self.assertEqual(6, cloner.generate_id())
        self.assertEqual(7, cloner.generate_id())

    def test_clone_subgraph_simple_branch(self):
        initial = EntityGraph(1)
        initial.add_entity(1, 'Name1')
        initial.add_entity(2, 'Name2')
        initial.add_entity(3, 'Name3')
        initial.add_link(1, 2)
        initial.add_link(2, 3)
        cloner = EntityCloner(initial)
        cloned = cloner.clone_subgraph()

        self.assertEqual(3, len(cloned.entities))
        self.assertEqual(cloned.get_entity(4).name, initial.get_entity(1).name)
        self.assertEqual(cloned.get_entity(5).name, initial.get_entity(2).name)
        self.assertEqual(cloned.get_entity(6).name, initial.get_entity(3).name)

        self.assertEqual(cloned.get_entity(4).children, {cloned.get_entity(5)})
        self.assertEqual(cloned.get_entity(5).children, {cloned.get_entity(6)})
        self.assertEqual(cloned.get_entity(6).children, set())

    def test_clone_subgraph_cycle(self):
        initial = EntityGraph(1)
        initial.add_entity(1, 'Name1')
        initial.add_entity(2, 'Name2')
        initial.add_entity(3, 'Name3')
        initial.add_link(1, 2)
        initial.add_link(2, 3)
        initial.add_link(3, 1)
        cloner = EntityCloner(initial)
        cloned = cloner.clone_subgraph()

        self.assertEqual(3, len(cloned.entities))
        self.assertEqual(cloned.get_entity(4).name, initial.get_entity(1).name)
        self.assertEqual(cloned.get_entity(5).name, initial.get_entity(2).name)
        self.assertEqual(cloned.get_entity(6).name, initial.get_entity(3).name)

        self.assertEqual(cloned.get_entity(4).children, {cloned.get_entity(5)})
        self.assertEqual(cloned.get_entity(5).children, {cloned.get_entity(6)})
        self.assertEqual(cloned.get_entity(6).children, {cloned.get_entity(4)})

    def test_clone_subgraph_with_complex_graph_with_cycle(self):
        initial = EntityGraph(2)
        initial.add_entity(1, 'Name1')
        initial.add_entity(2, 'Name2')
        initial.add_entity(3, 'Name3')
        initial.add_entity(4, 'Name4')
        initial.add_entity(5, 'Name5')
        initial.add_entity(6, 'Name6')

        initial.add_link(2, 1)
        initial.add_link(2, 3)
        initial.add_link(3, 4)
        initial.add_link(1, 3)
        initial.add_link(6, 2)
        initial.add_link(5, 1)

        def find_by_name(name, entities):
            return next(entity for entity in entities if entity.name == name)

        cloner = EntityCloner(initial)
        cloned = cloner.clone_subgraph()

        self.assertEqual(4, len(cloned.entities))
        self.assertEqual(cloned.get_entity(7).name, initial.get_entity(2).name)
        self.assertEqual(
            {child.entity_id for child in cloned.get_entity(7).children},
            {8, 9}
        )
        self.assertEqual(
            {child.name for child in cloned.get_entity(7).children},
            {'Name1', 'Name3'}
        )

        clone_of_1 = find_by_name('Name1', cloned.get_entity(7).children)
        clone_of_3 = find_by_name('Name3', cloned.get_entity(7).children)

        self.assertEqual(clone_of_1.children, {clone_of_3})
        self.assertEqual(clone_of_3.children, {cloned.get_entity(10)})
