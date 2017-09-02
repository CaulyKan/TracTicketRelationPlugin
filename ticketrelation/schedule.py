
from trac.core import Component, implements
from genshi.builder import tag
from genshi.filters import Transformer
from trac.web import ITemplateStreamFilter, IRequestHandler
from trac.ticket import TicketSystem, Ticket

class TicketScheduleSystem(Component):

    implements(IRequestHandler, ITemplateStreamFilter)


    # IRequestHandler methods

    def match_request(self, req):
        return req.path_info == '/ticket_schedule'

    def process_request(self, req):
        tid = req.args.id
        ts = TicketSystem(self.env)
        ticket = Ticket(self.env, tid)

    ## ITemplateStreamFilter

    def filter_stream(self, req, method, filename, stream, data):
        if filename == "ticket.html" and 'ticket' in data:
            ticket = data['ticket']
            trs = TicketRelationSystem(self.env)
            data = {}
            for relation in trs.build_relations().values():
                if relation.ticket_type_a == ticket['type']:
                    stream = self._generate_html(relation, relation.relation_type_a, 'a', stream, ticket, data)
                elif relation.ticket_type_b == ticket['type']:
                    stream = self._generate_html(relation, relation.relation_type_b, 'b', stream, ticket, data)

            add_script(req, 'ticketrelation/js/vue.js')
            add_script(req, 'ticketrelation/js/select_tickets.js')

            stream |= Transformer('//body').append(tag.script("""
                var data = %s;
                var app = new Vue({
                    el: '#properties',
                    data: {
                        relation: data,
                    }
                });
            """ % json.dumps(data)))

        return stream