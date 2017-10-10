# -*- coding: utf8 -*-
#
# Copyright (C) Cauly Kan, mail: cauliflower.kan@gmail.com
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
from datetime import datetime
from trac.core import Component, implements
from trac.util.datefmt import to_utimestamp, FixedOffset
from tracrpc.api import IXMLRPCHandler

from ticketrelation.api import Relation, TicketRelationSystem
from ticketrelation.schedule import TicketScheduleSystem
from ticketrelation.earn_value import EarnValueSystem

utc = FixedOffset(0, 'UTC')

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
        yield 'WIKI_VIEW', ((list,),), self.getScheduledTypes
        yield "WIKI_VIEW", ((dict, str, str), (dict, str, str, str)), self.getUserEarnValue
        yield "WIKI_VIEW", ((dict, str, str), (dict, str, str, str)), self.getUserEarnValueDetail

    def getTicketRelations(self, req):
        """
        Get definition of relations
        """

        ticket_relation_system = TicketRelationSystem(self.env)

        result = ticket_relation_system.build_relations()

        return [i.__dict__ for i in result.values()]

    def getScheduledTypes(self, req):
        """
        Get the types that should show shcedule
        """

        tss = TicketScheduleSystem(self.env)

        result = tss.get_scheduled_types()

        return result

    def getUserEarnValue(self, req, user, start_time, end_time=None):
        """
        Get a dict of user-earn value
        """

        evs = EarnValueSystem(self.env)

        start_time = to_utimestamp(datetime.strptime(start_time, '%Y-%m-%d').replace(tzinfo=utc))
        end_time = to_utimestamp(datetime.strptime(end_time, '%Y-%m-%d').replace(tzinfo=utc)) if end_time is not None else None

        users = evs.get_users(req, user)
        result = evs.get_users_ev(users, start_time, end_time)

        return result

    def getUserEarnValueDetail(self, req, user, start_time, end_time=None):
        """
        Get a dict of user-earn value detail
        """

        evs = EarnValueSystem(self.env)

        start_time = to_utimestamp(datetime.strptime(start_time, '%Y-%m-%d').replace(tzinfo=utc))
        end_time = to_utimestamp(datetime.strptime(end_time, '%Y-%m-%d').replace(tzinfo=utc)) if end_time is not None else None

        users = evs.get_users(req, user)
        result = evs.get_users_ev_detail(users, start_time, end_time)

        return result