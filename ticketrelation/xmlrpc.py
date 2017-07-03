# -*- coding: utf8 -*-
#
# Copyright (C) Cauly Kan, mail: cauliflower.kan@gmail.com
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

from trac.core import Component, implements
from tracrpc.api import IXMLRPCHandler

from ticketrelation.api import Relation, TicketRelationSystem


class TicketRelationRPC(Component):
    """
    Interface to ticket relation definitions.
    """

    implements(IXMLRPCHandler)

    def __init__(self):
        pass

    def xmlrpc_namespace(self):
        return 'ticketrelation'

    def xmlrpc_methods(self):
        yield 'WIKI_VIEW', ((dict,),), self.getTicketRelations

    def getTicketRelations(self, req):
        """
        Get definition of relations
        """

        ticket_relation_system = TicketRelationSystem(self.env)

        result = ticket_relation_system.build_relations()

        return result
