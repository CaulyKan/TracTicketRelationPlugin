import json
import re
import random
from datetime import datetime
from itertools import groupby
from trac.core import Component, implements
from genshi.builder import tag
from genshi.filters import Transformer
from trac.web import ITemplateStreamFilter, IRequestHandler
from trac.ticket import TicketSystem, Ticket
from trac.web.chrome import add_stylesheet, add_script
from trac.wiki.macros import WikiMacroBase, MacroError
from trac.ticket.query import TicketQueryMacro, Query, QuerySyntaxError, QueryValueError
from trac.ticket.model import Type

from .api import TicketRelationSystem

class TicketScheduleSystem(Component):

    implements(IRequestHandler, ITemplateStreamFilter)


    # IRequestHandler methods

    def match_request(self, req):
        return req.path_info == '/ticket_schedule'

    def process_request(self, req):
        tid = req.args.id
        ticket = Ticket(self.env, tid)
        result = self._get_schedule_info(ticket)
        json_result = json.dumps(result, cls=DateTimeEncoder)
        req.send(json_result, 'application/json')


    ## ITemplateStreamFilter

    def filter_stream(self, req, method, filename, stream, data):
        if filename == "ticket.html" and 'ticket' in data:
            ticket = data['ticket']

            if ticket.id > 0 and self._have_schedule(ticket):

                add_stylesheet(req, 'ticketrelation/css/schedule.css')

                schedule = self._get_schedule_info(ticket)

                stream |= Transformer('//div[@id="ticket"]').after(
                    tag.div(
                        tag.h3(
                            tag.a('Schedule', id='schedule_label', href='#schedule_label'),
                        class_='foldable'),
                        tag.div(tag.schedule(**{':schedule': 'schedule', ':config': 'config'}), class_='schedule_container', id='schedule_container'),
                    id='schedule')
                )

                config = {
                    'url': req.base_url,
                    'startDate': None,
                    'finishDate': None,
                    'showUnavailable': 1
                }

                stream |= Transformer('//body').append(tag.script("""
                    $(window).load(function() {
                        var data = %s;
                        var config = %s;
                        var app = new Vue({
                            el: '#schedule_container',
                            data: {
                                schedule: data,
                                config: config,
                            }
                        });
                    });
                """ % (json.dumps(schedule, cls=DateTimeEncoder), json.dumps(config, cls=DateTimeEncoder))))

        return stream

    def get_scheduled_types(self):
        types = Type.select(self.env)
        config = self.config['ticket-relation-schedule']
        return [t.name for t in types if config.getbool(t.name + '.show_schedule', False)]

    def get_schedule(self, tickets):

        return [{'id': x.id if hasattr(x, 'id') else x['id'], 'summary': x['summary'], 'status': x['status'], 'owner': x['owner'],
                 'activity_started_date': x['activity_started_date'], 'activity_start_date': x['activity_start_date'],
                 'activity_finished_date': x['activity_finished_date'], 'activity_finish_date': x['activity_finish_date']}
                for x in tickets]

    def _get_schedule_info(self, ticket):
        trs = TicketRelationSystem(self.env)
        config = self.config['ticket-relation-schedule']
        result = {}

        for relation in trs.build_relations().values():
            target_role = ''
            if relation.ticket_type_a == ticket['type']:
                target_role = 'b'
            elif relation.ticket_type_b == ticket['type']:
                target_role = 'a'

            if target_role != '' and config.getbool(relation.get_ticket_type(target_role) + '.show_schedule', False):
                target_tickets = trs.get_relations(ticket, relation, trs.opposite(target_role))
                result[relation.name + '_' + target_role + ',' + relation.get_label(trs.opposite(target_role))] = \
                    self.get_schedule(target_tickets)

        if config.getbool(ticket['type'] + '.show_schedule', False):
            x = ticket
            result['this,' + ticket['summary']] = \
                [{'id': x.id, 'summary': x['summary'], 'status': x['status'], 'owner': x['owner'],
                 'activity_started_date': x['activity_started_date'], 'activity_start_date': x['activity_start_date'],
                 'activity_finished_date': x['activity_finished_date'], 'activity_finish_date': x['activity_finish_date']}]

        return result

    def _have_schedule(self, ticket):
        trs = TicketRelationSystem(self.env)
        config = self.config['ticket-relation-schedule']
        for relation in trs.build_relations().values():
            target_role = ''
            if relation.ticket_type_a == ticket['type']:
                target_role = 'b'
            elif relation.ticket_type_b == ticket['type']:
                target_role = 'a'
            if target_role != '' and config.getbool(relation.get_ticket_type(target_role) + '.show_schedule', False):
                return True

        if config.getbool(ticket['type'] + '.show_schedule', False):
            return True
        return False


class ScheduleMacro(WikiMacroBase):
    realm = TicketSystem.realm

    def expand_macro(self, formatter, name, content):
        req = formatter.req
        query_string = TicketQueryMacro.parse_args(content)[0]

        kwargs = dict([item.split('=') for item in content.split(',')[1:]])

        try:
            query = Query.from_string(self.env, query_string)
        except QuerySyntaxError as e:
            raise MacroError(e)

        try:
            tickets = query.execute(req)
        except QueryValueError as e:
            raise MacroError(e)

        # Formats above had their own permission checks, here we need to
        # do it explicitly:

        tickets = [t for t in tickets
                   if 'TICKET_VIEW' in req.perm(self.realm, t['id'])]

        tickets = map(lambda x: Ticket(self.env, x['id']), tickets)

        schedule_info = {'test': TicketScheduleSystem(self.env).get_schedule(tickets)}

        add_script(req, 'ticketrelation/js/bundle.js')
        add_stylesheet(req, 'ticketrelation/css/schedule.css')

        random_id = str(random.randint(0, 10000))

        config = {
            'url': req.base_url,
            'startDate': kwargs.get('startdate', None),
            'finishDate': kwargs.get('finishdate', None),
            'showUnavailable': kwargs.get('showunavailable', 1)
        }

        return tag.div(tag.div(
            tag.schedule(**{':schedule': 'schedule', ':config': 'config'}), class_='schedule_container', id='schedule_container_' + random_id),
            tag.script("""         
                $(window).load(function() {
                    var data = %s;
                    var config = %s;
                    var app = new window.Vue({
                        el: '#schedule_container_%s',
                        data: {
                            schedule: data,
                            config: config,
                        }
                    });
                });""" % (json.dumps(schedule_info, cls=DateTimeEncoder), json.dumps(config, cls=DateTimeEncoder), random_id))
        )

    def is_inline(self, content):
        return False


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)
