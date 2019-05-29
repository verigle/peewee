import sys

from peewee import ColumnBase
from peewee import Node
from peewee import SQL


PE_KEY = 'key'
PE_INDEX = 'index'
PE_FUNCTION = 'function'
PE_FILTER = 'filter'
PE_ANY = 'any'


if sys.version_info[0] > 2:
    basestring = str


class _PathElement(Node):
    __slots__ = ('element', 'typ')

    def __init__(self, element):
        if isinstance(element, basestring):
            typ = PE_KEY
        elif isinstance(element, int):
            typ = PE_INDEX
        elif isinstance(element, _PathFunction):
            typ = PE_FILTER if element.as_filter else PE_FUNCTION
        elif isinstance(element, _PathExpr):
            typ = PE_FILTER
        elif element is Ellipsis:
            typ = PE_ANY
        else:
            raise ValueError('invalid path element: %r' % element)
        self.element = element
        self.typ = typ

    def __call__(self):
        if self.typ != PE_KEY:
            raise ValueError('path element does not support function call')
        return _PathElement(_PathFunction(self.element))

    def __sql__(self, ctx):
        if self.typ == PE_INDEX:
            ctx.literal('[%s]' % self.element)
        elif self.typ == PE_ANY:
            ctx.literal('[*]')
        elif self.typ == PE_KEY:
            if self.element.find(' ') >= 0:
                ctx.literal('."%s"' % self.element)
            else:
                ctx.literal('.%s' % self.element)
        elif self.typ == PE_FUNCTION:
            ctx.sql(self.element)
        elif self.typ == PE_FILTER:
            ctx.literal(' ? ').sql(self.element)
        else:
            assert False, 'should not get here!'
        return ctx


class _Path(ColumnBase):
    def __init__(self, path=None):
        self.path = path or []
        super(_Path, self).__init__()

    def __getitem__(self, item):
        element = _PathElement(item)
        return _Path(self.path + [element])
    __getattr__ = __getitem__

    def __call__(self):
        if not self.path:
            raise ValueError('Cannot emulate function on empty path.')
        path = list(self.path)
        element = path.pop()
        return _Path(path + [element()])

    def __px__(op):
        def inner(self, rhs):
            return _PathExpr(self, op, rhs)
        return inner
    __eq__ = __px__('==')
    __ge__ = __px__('>=')
    __gt__ = __px__('>')
    __le__ = __px__('<=')
    __lt__ = __px__('<')
    __ne__ = __px__('!=')
    like_regex = __px__('like_regex')
    startswith = __px__('starts with')

    def filter(self, expr):
        if not isinstance(expr, (_PathExpr, _PathFunction)):
            raise ValueError('filter predicate must be path expression')
        return _Path(self.path + [_PathElement(expr)])

    def exists(self, expr):
        return _PathFunction('exists', expr, as_filter=True)

    def __sql__(self, ctx):
        ctx.literal('@' if ctx.state.path_nested else '\'$')

        with ctx(path_nested=True):
            for item in self.path:
                if not isinstance(item, _PathElement):
                    raise ValueError('unexpected item in path: %r' % item)
                ctx.sql(item)

        if not ctx.state.path_nested:
            ctx.literal("'")
        return ctx


class _PathFunction(_Path):
    def __init__(self, name, arg=None, as_filter=False):
        self.name = name
        self.arg = arg
        self.as_filter = as_filter
        super(_PathFunction, self).__init__([])

    def __sql__(self, ctx):
        with ctx(parentheses=self.as_filter):
            if not self.as_filter:
                ctx.literal('.')
            ctx.literal(self.name)
            with ctx(parentheses=True):
                if self.arg is not None:
                    ctx.sql(self.arg)
        return ctx


class _PathExpr(_Path):
    def __init__(self, lhs, op, rhs):
        self.lhs = lhs
        self.op = op
        self.rhs = rhs
        super(_PathExpr, self).__init__([])

    def __and__(self, rhs):
        return _PathExpr(self, '&&', rhs)
    def __or__(self, rhs):
        return _PathExpr(self, '||', rhs)

    def __sql__(self, ctx):
        if not isinstance(self.rhs, Node):
            if isinstance(self.rhs, basestring):
                rhs = '"%s"' % self.rhs
            elif isinstance(self.rhs, int):
                rhs = str(self.rhs).lower()
            elif self.rhs is None:
                rhs = 'null'
            else:
                raise ValueError('invalid value for right-hand-side of path '
                                 'filter expression')
            rhs = SQL(rhs)
        else:
            rhs = self.rhs

        with ctx(parentheses=True):
            return ctx.sql(self.lhs).literal(' %s ' % self.op).sql(rhs)


# Factory for building paths and filter-expressions.
P = _Path()
