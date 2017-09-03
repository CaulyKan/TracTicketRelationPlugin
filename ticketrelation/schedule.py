import json
from trac.core import Component, implements
from genshi.builder import tag
from genshi.filters import Transformer
from trac.web import ITemplateStreamFilter, IRequestHandler
from trac.ticket import TicketSystem, Ticket
from trac.web.chrome import add_stylesheet
from .api import TicketRelationSystem
from trac.util import to_list
from datetime import datetime
from genshi.input import HTML

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

            if self._have_schedule(ticket):

                add_stylesheet(req, 'ticketrelation/css/schedule.css')

                schedule = self._get_schedule_info(ticket)

                stream |= Transformer('//div[@id="ticket"]').after(
                    tag.div(
                        tag.h3(
                            tag.a('Schedule', id='schedule_label', href='#schedule_label'),
                        class_='foldable'),
                        tag.div(tag.schedule(**{':schedule': 'schedule'}), id='schedule_container'),
                    id='schedule')
                )

                stream |= Transformer('//body').append(tag.script("""
                (function() {
                    var data = %s;
                    var app = new Vue({
                        el: '#schedule_container',
                        data: {
                            schedule: data,
                        }
                    });
                })();
                """ % (json.dumps(schedule, cls=DateTimeEncoder), )))

        return stream

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
                    [
                        {'id': x.id, 'summary': x['summary'], 'status': x['status'], 'owner': x['owner'],
                         'activity_started_date': x['activity_started_date'], 'activity_start_date': x['activity_start_date'],
                         'activity_finished_date': x['activity_finished_date'], 'activity_finish_date': x['activity_finish_date']}
                        for x in target_tickets
                    ]

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


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)
