# -*- coding: utf-8 -*-

from django.db.models import Q
from functools import reduce

class RQLSemantics:
    OPERATORS = {
        'contains': '==**',
        'startswith': '==*',
        'endswith': '== *',
        'range': '=in=',
        'isnull': '=isnull=',
        'exact': '==',
        'in': '=in=',
        'not_in': '=out=',
        'eq': '==',
        'ne': '!=',
        'lte': '<=',
        'lt': '<',
        'gte': '>=',
        'gt': '>'

    }


    """
    filter[user__email.contains]=qwe
    """



    # OPERATORS = {
    #     '==': 'eq',
    #     '!=': 'ne',
    #     '=ne=': 'ne',
    #     '<=': 'lte',
    #     '=le=': 'lte',
    #     '<': 'lt',
    #     '=lt=': 'lt',
    #     '>=': 'gte',
    #     '=ge=': 'gte',
    #     '>': 'gt',
    #     '=gt=': 'gt',
    #     '=in=': 'in',
    #     '=out=': 'out',
    # }

    def _default(self, ast):
        return ast

    def OREXPRESSION(self, ast):
        return reduce(lambda a, b: a | b, ast)

    def ANDEXPRESSION(self, ast):
        return reduce(lambda a, b: a & b, ast)

    def COMPARISON(self, ast):
        field, operator, value = ast
        operator = self.OPERATORS[operator]
        negate = False

        if operator == 'out':
            operator = 'in'
            negate = True
        elif operator == 'ne':
            operator = 'eq'
            negate = True

        if operator != 'eq':
            field = '%s__%s' % (field, operator)

        q = Q(**{field: value})

        if negate:
            q = ~q

        return q
