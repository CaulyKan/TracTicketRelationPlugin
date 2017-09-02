import json

from trac.core import *
from trac.web.api import IRequestHandler, ITemplateStreamFilter
from trac.web.chrome import ITemplateProvider, add_script
from trac.ticket.query import Query, QueryModule
from trac.ticket.model import Ticket
from genshi.builder import tag
from genshi.filters import Transformer
from genshi.input import HTML
from genshi.template import MarkupTemplate
from .api import TicketRelationSystem

import pkg_resources

class SelectTicketPlugin(Component):

    implements(IRequestHandler, ITemplateProvider, ITemplateStreamFilter)

    # IRequestHandler methods

    def match_request(self, req):
        return req.path_info == '/select_tickets'

    def process_request(self, req):
        args = req.args
        qm = QueryModule(self.env)
        template, data, _whatever = qm.process_request(req)
        return 'select_tickets.html', data, None

    #ITemplateProvider methods
    def get_htdocs_dirs(self):
        return [('ticketrelation', pkg_resources.resource_filename('ticketrelation', 'htdocs'))]

    def get_templates_dirs(self):
        return [pkg_resources.resource_filename('ticketrelation', 'templates')]


    ## ITemplateStreamFilter

    def filter_stream(self, req, method, filename, stream, data):
        if req.path_info == '/select_tickets':
            stream |= Transformer('//div[@id="banner"]').remove()
            stream |= Transformer('//div[@id="mainnav"]').remove()
            stream |= Transformer('//div[@id="ctxtnav"]').remove()

        if (filename == "ticket.html" or filename == 'ticket_preview.html') and 'ticket' in data:
            ticket = data['ticket']
            trs = TicketRelationSystem(self.env)
            data = {}
            for relation in trs.build_relations().values():
                if relation.ticket_type_a == ticket['type']:
                    stream = self._generate_html(relation, relation.relation_type_a, 'a', stream, ticket, data)
                elif relation.ticket_type_b == ticket['type']:
                    stream = self._generate_html(relation, relation.relation_type_b, 'b', stream, ticket, data)

            add_script(req, 'ticketrelation/js/select_tickets_bundle.js')

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

    def _generate_html(self, relation, relation_type, relation_role, stream, ticket, data):

        trs = TicketRelationSystem(self.env)
        try:
            if relation_type == 'one':
                if ticket[relation.name + '_' + relation_role] is not None:
                    stream |= Transformer(
                        '//input[@id="field-%s_%s"]' % (relation.name, relation_role)) \
                        .replace(HTML("""
                            <relation-single id="field-%s_%s" :relation="relation['%s_%s']" />
                        """ % (relation.name, relation_role, relation.name, relation_role)))
            else:
                if ticket[relation.name + '_' + relation_role] is not None:
                    stream |= Transformer(
                        '//textarea[@id="field-%s_%s"]' % (relation.name, relation_role)) \
                        .replace(HTML("""
                            <relation-multi id="field-%s_%s" :relation="relation['%s_%s']" />
                        """ % (relation.name, relation_role, relation.name, relation_role)))

            data[relation.name + '_' + relation_role] = {
                'name': relation.name,
                'role': relation_role,
                'targetType': relation.ticket_type_a if relation_role == 'b' else relation.ticket_type_b,
                'value': ticket[relation.name + '_' + relation_role]
            }

        except Exception as e:
            self.log.error(e)
            return stream

        return stream
