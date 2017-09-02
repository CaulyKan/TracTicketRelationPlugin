
from trac.core import Component, implements
from trac.web import ITemplateStreamFilter
from trac.ticket import ITicketManipulator, ITicketChangeListener
from trac.ticket.model import Ticket, TicketSystem
from genshi.filters import Transformer
from genshi.builder import tag

import re

NUMBERS_RE = re.compile(r'\d+', re.U)
VALID_RELATION = re.compile(r'^[\d, ]+$')


class TicketRelationSystem(Component):

    implements(
               #ITemplateProvider,
               ITemplateStreamFilter,
               ITicketChangeListener,
               #ITicketManipulator
    )


    _relations = None
    _relations_ready = False
    def build_relations(self):
        """
        Build relation model from config.

        [ticket-relation]
        subticket_relation = bug -> bug
        subticket_relation.type = many -> many
        subticket_relation.label = Parent Tickets -> Child Tickets
        """

        if not self._relations_ready:
            self._relations = {}

            for name in [i for i in self.config['ticket-relation'] if not '.' in i]:
                try:
                    self._relations [name] = Relation(name, self.config)
                except Exception as e:
                    self.log.warning(e.message)

            self.check_and_create_fields(self._relations )
            return self._relations

        else:
            return self._relations

    def check_and_create_fields(self, relations):
        """
        Check and create the custom fields required by ticket-relations and save in config
        """

        dirty = False
        config = self.config['ticket-custom']

        for relation in relations.values():
            if relation.name + '_a' not in config:
                config.set(relation.name + '_a', 'text' if relation.relation_type_a == 'one' else 'textarea')
                config.set(relation.name + '_a.label', relation.label_a)
                config.set(relation.name + '_a.relation_type', relation.relation_type_a)
                if relation.relation_type_a == 'many':
                    config.set(relation.name + '_a.format', 'summary,status,owner')
                dirty = True
            if relation.name + '_b' not in config:
                config.set(relation.name + '_b', 'text' if relation.relation_type_b == 'one' else 'textarea')
                config.set(relation.name + '_b.label', relation.label_b)
                config.set(relation.name + '_b.relation_type', relation.relation_type_b)
                if relation.relation_type_b == 'many':
                    config.set(relation.name + '_b.format', 'summary,status,owner')
                dirty = True

        if dirty:
            self.config.save()

    # ITicketChangeListener methods
    def ticket_created(self, ticket):
        pass

    def ticket_deleted(self, ticket):

        def _relation_changed(relation, role):

            relations = set(NUMBERS_RE.findall(ticket[relation.name + '_' + role] or ''))

            for target_ticket in relations:
                xticket = Ticket(self.env, target_ticket)
                if self.remove_relation(xticket, ticket.id, relation.name, self.opposite(role)):
                    xticket.save_changes('', '(#%s %s) %s' % (ticket.id, ticket['summary'], 'Ticket deleted.'))

        for relation in self.build_relations().values():

            if relation.ticket_type_a == ticket['type']:
                _relation_changed(relation, 'a')
            if relation.ticket_type_b == ticket['type']:
                _relation_changed(relation, 'b')

    def ticket_changed(self, ticket, comment, author, old_values):

        def _relation_changed(relation, role):

            old_relations = old_values.get(relation.name + '_' + role, '') or ''
            old_relations = set(NUMBERS_RE.findall(old_relations))
            new_relations = set(NUMBERS_RE.findall(ticket[relation.name + '_' + role] or ''))

            if new_relations == old_relations:
                return

            # remove old relations
            for target_ticket in old_relations - new_relations:
                xticket = Ticket(self.env, target_ticket)
                if self.remove_relation(xticket, ticket.id, relation.name, self.opposite(role)):
                    xticket.save_changes(author, '(#%s %s) %s' % (ticket.id, ticket['summary'], comment))

            # add new relations
            for target_ticket in new_relations - old_relations:
                xticket = Ticket(self.env, target_ticket)
                if self.add_relation(xticket, ticket.id, relation.name, self.opposite(role)):
                    xticket.save_changes(author, '(#%s %s) %s' % (ticket.id, ticket['summary'], comment))

        for relation in self.build_relations().values():

            if relation.ticket_type_a == ticket['type']:
                _relation_changed(relation, 'a')
            if relation.ticket_type_b == ticket['type']:
                _relation_changed(relation, 'b')

    def opposite(self, role):
        return 'a' if role == 'b' else 'b'

    def remove_relation(self, ticket, id, relation, role):
        value = ticket[relation+ '_' + role]
        ids = map(unicode.strip, value.split(',')) if value is not None else []
        if str(id) in ids:
            if '' in ids: ids.remove('')
            ids.remove(str(id))
            ticket[relation+ '_' + role] = ','.join(ids)
            return True
        else:
            return False

    def add_relation(self, ticket, id, relation, role):
        value = ticket[relation + '_' + role]
        ids = map(unicode.strip, value.split(',')) if value is not None else []
        if not str(id) in ids:
            if '' in ids: ids.remove('')
            ids.append(str(id))
            ticket[relation+ '_' + role] = ','.join(ids)
            return True
        else:
            return False

    # ITicketManipulator methods
    def prepare_ticket(self, req, ticket, fields, actions):
        pass

    def validate_ticket(self, req, ticket):

        def _relation_validate(relation, role):
            if not VALID_RELATION.match(ticket.get(relation.name + '_' + role), ''):
                return 'Invalid relation.'

        result = []

        for relation in self.build_relations().values():
            if relation.ticket_type_a == ticket['type']:
                result.append(_relation_validate(relation, 'a'))
            if relation.ticket_type_b == ticket['type']:
                result.append(_relation_validate(relation, 'b'))

    def filter_stream(self, req, method, filename, stream, data):

        if filename != "ticket.html" and filename != 'ticket_preview.html':
            return stream

        if 'ticket' in data:
            ticket = data['ticket']

            stream |= Transformer('//head').append(tag.style("""
                .relation_table {
                    width: 100%;
                }
                .relation_table td {
                    border-bottom: dotted 1px #eed;
                }
            """))

            for relation in self.build_relations().values():
                if relation.ticket_type_a == ticket['type']:
                    stream = self._generate_html(relation, relation.relation_type_a, 'a', stream, ticket)
                elif relation.ticket_type_b == ticket['type']:
                    stream = self._generate_html(relation, relation.relation_type_b, 'b', stream, ticket)

        return stream

    def _generate_html(self, relation, relation_type, relation_role, stream, ticket):
        config = self.config['ticket-custom']
        try:
            if relation_type == 'one':
                if ticket[relation.name + '_' + relation_role] is not None:
                    target_ticket = Ticket(self.env, int(ticket[relation.name + '_' + relation_role]))

                    stream |= Transformer('//div[@id="ticket"]//td[@headers="h_%s"]/text()' % (relation.name + '_' + relation_role)) \
                        .replace(tag.a('#%s %s' % (target_ticket.id, target_ticket['summary']), href='/ticket/' + str(target_ticket.id)))
            else:
                if ticket[relation.name + '_' + relation_role] is not None:
                    target_tickets = [Ticket(self.env, int(i)) for i in ticket[relation.name + '_' + relation_role].split(',')]
                    format = map(unicode.strip, config.get(relation.name + '_' + relation_role + '.format').split(','))

                    tbody = tag.tbody()
                    for target_ticket in target_tickets:
                        columns = [tag.td(tag.a('#' + str(target_ticket.id), href='/ticket/' + str(target_ticket.id)))]
                        columns.extend([tag.td(target_ticket[field]) for field in format])
                        tbody.append(tag.tr(*columns))

                    stream |= Transformer('//div[@id="ticket"]//td[@headers="h_%s"]/text()' % (relation.name + '_' + relation_role)) \
                        .replace(tag.table(tbody, class_='relation_table'))
        except Exception as e:
            self.log.error(e.message)

        return stream

class Relation(object):

    def __init__(self, name, config):

        self.name = name
        self.ticket_type_a = None
        self.ticket_type_b = None
        self.relation_type_a = None
        self.relation_type_b = None
        self.label_a = None
        self.label_b = None

        try:
            for opt_name, opt_value in config.options('ticket-relation'):

                if opt_name.startswith(name):

                    if opt_name == name:
                        self.ticket_type_a, self.ticket_type_b = map(unicode.strip, opt_value.split('->'))

                    elif opt_name == name + '.type':
                        self.relation_type_b, self.relation_type_a = map(unicode.strip, opt_value.split('->'))
                        self.relation_type_a = 'one' if self.relation_type_a == 'one' else 'many'
                        self.relation_type_b = 'one' if self.relation_type_b == 'one' else 'many'

                    elif opt_name == name + '.label':
                        self.label_b, self.label_a = map(unicode.strip, opt_value.split('->'))

            if None in [self.ticket_type_a, self.ticket_type_b, self.relation_type_a, self.relation_type_b, self.label_a, self.label_b]:
                raise Exception()

        except:

            raise Exception('Ticket Relation: %s is not properly configured.' % name)
