from peewee import *
from playhouse.jsonpath import P

from .base import BaseTestCase


class TestJsonPath(BaseTestCase):
    def assertPath(self, p, expected):
        sql, params = Context().parse(p)
        self.assertEqual(sql, "'%s'" % expected)
        self.assertEqual(params, [])

    def test_path_filter(self):
        # Simple filter expression.
        self.assertPath(P.filter(P == 'foo'), '$ ? (@ == "foo")')

        # Filter expression on sub-elements.
        self.assertPath(P.items[...].filter(P > 50), '$.items[*] ? (@ > 50)')
        self.assertPath(P.items[2].filter(P == 12), '$.items[2] ? (@ == 12)')

        # Combined filter expression.
        self.assertPath(P.items[...].filter((P == 1) | (P == 3)),
                        '$.items[*] ? ((@ == 1) || (@ == 3))')

        # Chained filter expressions.
        p = P.filter(P.items[...] == 'k1').filter(P.items[...] == 'k3')
        self.assertPath(p, '$ ? (@.items[*] == "k1") ? (@.items[*] == "k3")')

        # Special method.
        self.assertPath(P.tags.filter(P[0].startswith('od')),
                        '$.tags ? (@[0] starts with "od")')

        # Special function.
        path = P.tags.filter(P.exists(P.filter(P == 'prime')))
        self.assertPath(path, '$.tags ? (exists(@ ? (@ == "prime")))')

        # Functions.
        path = P.meta.filter(P.follow.size() == 0)
        self.assertPath(path, '$.meta ? (@.follow.size() == 0)')

        path = P.meta.filter(P.precede.size() < P.follow.size())
        self.assertPath(path, '$.meta ? (@.precede.size() < @.follow.size())')

        # Multi-filter.
        path = (P
                .filter(P.intervals[...] < 12)
                .filter(P.meta.precede[...] == 3)
                .filter(P.meta.follow[...] == 5))
        self.assertPath(path, ('$ ? (@.intervals[*] < 12) '
                               '? (@.meta.precede[*] == 3) '
                               '? (@.meta.follow[*] == 5)'))
