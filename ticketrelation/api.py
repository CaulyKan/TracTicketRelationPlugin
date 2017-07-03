
from trac.core import Component, implements
from trac.env import IEnvironmentSetupParticipant
from trac.db import DatabaseManager
from trac.web.chrome import ITemplateProvider
from trac.web import ITemplateStreamFilter
from trac.ticket import ITicketManipulator, ITicketChangeListener
from trac.ticket.model import Ticket, TicketSystem
from trac.ticket.notification import TicketNotifyEmail
from genshi.filters import Transformer
from genshi.builder import tag

import re
import db_default

NUMBERS_RE = re.compile(r'\d+', re.U)
VALID_RELATION = re.compile(r'^[\d, ]+$')


class TicketRelationSystem(Component):

    implements(IEnvironmentSetupParticipant,
               #ITemplateProvider,
               ITemplateStreamFilter,
               ITicketChangeListener,
               #ITicketManipulator
    )

    def __init__(self):
        self.found_db_version = 0

    # ITemplateProvider methods
    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('ticketrelation', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [('ticketrelation', resource_filename(__name__, 'templates'))]

    # IEnvironmentSetupParticipant methods

    def environment_created(self):
        self.upgrade_environment()

    def environment_needs_upgrade(self, db):
        cursor = db.cursor()
        cursor.execute("""
                    SELECT value FROM system WHERE name=%s
                    """, (db_default.name,))
        value = cursor.fetchone()
        try:
            self.found_db_version = int(value[0])
            if self.found_db_version < db_default.version:
                return True
        except:
            return True

        return False

    def upgrade_environment(self, db=None):
        db_manager, _ = DatabaseManager(self.env)._get_connector()

        # update the version
        with self.env.db_transaction as db:
            old_data = {}  # {table.name: (cols, rows)}
            cursor = db.cursor()
            if not self.found_db_version:
                cursor.execute("""
                     INSERT INTO system (name, value) VALUES (%s, %s)
                     """, (db_default.name, db_default.version))
            else:
                cursor.execute("""
                     UPDATE system SET value=%s WHERE name=%s
                     """, (db_default.version, db_default.name))

                for table in db_default.tables:
                    cursor.execute("""
                         SELECT * FROM """ + table.name)
                    cols = [x[0] for x in cursor.description]
                    rows = cursor.fetchall()
                    old_data[table.name] = (cols, rows)
                    cursor.execute("""
                         DROP TABLE """ + table.name)

            # insert the default table
            for table in db_default.tables:
                for sql in db_manager.to_sql(table):
                    cursor.execute(sql)

                # add old data
                if table.name in old_data:
                    cols, rows = old_data[table.name]
                    sql = """
                         INSERT INTO %s (%s) VALUES (%s)
                         """ % (table.name, ','.join(cols), ','.join(['%s'] * len(cols)))
                    for row in rows:
                        cursor.execute(sql, row)

        relation = self.build_relations()
        self.check_and_create_fields(relation)

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
        with self.env.db_transaction as db:
            for relation_name, role, tid in db('SELECT relation, "a", a FROM ticket_relation WHERE b=%s '
                                               'UNION ALL '
                                               'SELECT relation, "b", b FROM ticket_relation WHERE a=%s'):
                xticket = Ticket(self.env, tid)
                self.remove_relation(xticket, tid, relation_name, role)

            cursor = db.cursor()
            cursor.execute("""
                DELETE FROM ticket_relation WHERE a=%s OR b=%s
                """, (ticket.id, ))

    def ticket_changed(self, ticket, comment, author, old_values):

        def _relation_changed(relation, role):

            with self.env.db_transaction as db:
                cursor = db.cursor()

                old_relations = old_values.get(relation.name + '_' + role, '') or ''
                old_relations = set(NUMBERS_RE.findall(old_relations))
                new_relations = set(NUMBERS_RE.findall(ticket[relation.name + '_' + role] or ''))

                if new_relations == old_relations:
                    return

                # remove old relations
                for target_ticket in old_relations - new_relations:
                    sql = 'DELETE FROM ticket_relation WHERE %s=%s AND relation=%s AND %s=%s'
                    cursor.execute(sql, (role, ticket.id, relation.name, self.opposite(role), int(target_ticket.id)))
                    xticket = Ticket(self.env, target_ticket)
                    self.remove_relation(xticket, ticket.id, relation.name, self.opposite(role))
                    xticket.save_changes(author, '(#%s %s) %s' % (ticket.id, ticket['summary'], comment))

                # add new relations
                for target_ticket in new_relations - old_relations:
                    sql = 'INSERT INTO ticket_relation(a, b, relation) VALUES(%s, %s, %s)'
                    cursor.execute(sql, (ticket.id, int(target_ticket), relation.name) if role == 'a' else (target_ticket, ticket.id, relation.name))
                    xticket = Ticket(self.env, target_ticket)
                    self.add_relation(xticket, ticket.id, relation.name, self.opposite(role))
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
            ids.remove(str(id))
            ticket[relation+ '_' + role] = ','.join(ids)
            return True
        else:
            return False

    def add_relation(self, ticket, id, relation, role):
        value = ticket[relation + '_' + role]
        ids = map(unicode.strip, value.split(',')) if value is not None else []
        if not str(id) in ids:
            ids.append(id)
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
