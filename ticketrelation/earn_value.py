import re

import datetime
from trac.core import Component, implements
from trac.perm import PermissionSystem
from trac.ticket import ITicketActionController, IEnvironmentSetupParticipant, TicketSystem, ConfigurableTicketWorkflow
from trac.ticket.query import TicketQueryMacro
from trac.util.datefmt import to_utimestamp, datetime_now, FixedOffset
from trac.wiki.macros import WikiMacroBase, MacroError
from trac.db import Table, Column, DatabaseManager, TracError
from genshi.builder import tag


class EarnValueSystem(Component):

    implements(ITicketActionController, IEnvironmentSetupParticipant)

    table_name = 'earn_value'

    def get_table(self):

        return Table(self.table_name) [
            Column('ticket', type='int'),
            Column('type'),
            Column('action'),
            Column('value', type='float'),
            Column('user'),
            Column('time', type='int'),
            Column('changeid', type='int'),
        ]

    def environment_created(self):
        self.upgrade_environment()

    def environment_needs_upgrade(self, db=None):
        dburi = self.config.get('trac', 'database')
        with self.env.db_query as db:
            cursor = db.cursor()
            tables = self._get_tables(dburi, cursor)
            if self.table_name in tables:
                return False
            else:
                return True

    def upgrade_environment(self, db=None):
        db_manager, _ = DatabaseManager(self.env)._get_connector()
        with self.env.db_transaction as db:
            cursor = db.cursor()
            for sql in db_manager.to_sql(self.get_table()):
                cursor.execute(sql)

    def _get_tables(self, dburi, cursor):
        """Code from TracMigratePlugin by Jun Omae (see tracmigrate.admin)."""
        if dburi.startswith('sqlite:'):
            sql = """
                SELECT name
                  FROM sqlite_master
                 WHERE type='table'
                   AND NOT name='sqlite_sequence'
            """
        elif dburi.startswith('postgres:'):
            sql = """
                SELECT tablename
                  FROM pg_tables
                 WHERE schemaname = ANY (current_schemas(false))
            """
        elif dburi.startswith('mysql:'):
            sql = "SHOW TABLES"
        else:
            raise TracError('Unsupported database type "%s"'
                            % dburi.split(':')[0])
        cursor.execute(sql)
        return sorted([row[0] for row in cursor])

    # ITicketActionController methods
    def get_configurable_workflow(self):
        controllers = TicketSystem(self.env).action_controllers
        for controller in controllers:
            if isinstance(controller, ConfigurableTicketWorkflow):
                return controller
        return ConfigurableTicketWorkflow(self.env)

    def get_ticket_actions(self, req, ticket):
        controller = self.get_configurable_workflow()
        return controller.get_actions_by_operation_for_req(req, ticket, 'earn_value')

    def get_all_status(self):
        return []

    def render_ticket_action_control(self, req, ticket, action):
        actions = self.get_configurable_workflow().actions
        label = actions[action]['name']
        return label, '', ''

    def get_ticket_changes(self, req, ticket, action):
        return {}

    def apply_action_side_effects(self, req, ticket, action):
        config = self.config['ticket-workflow']
        if config.get(action + '.earn_value', '') != '':

            value = 0
            time = to_utimestamp(datetime_now(FixedOffset(0, 'UTC')))
            try:
                evdef = config.get(action + '.earn_value', '').strip()
                if evdef.isdigit():
                    value = float(evdef)
                elif evdef.endswith('%') and 'activity_earn_value' in ticket:
                    value = float(ticket['activity_earn_value']) * float(evdef[:-1]) / 100

            except Exception as e:
                self.log.warning(e)

            with self.env.db_transaction as db:
                cursor = db.cursor()
                cursor.execute("""
                    INSERT INTO earn_value VALUES (%s, %s, %s, %s, %s, %s, %s);
                """, (ticket.id, 'workflow', action, value, req.authname, time, 0))

        if config.get(action + '.update_time', '') != '':
            field = config.get(action + '.update_time').strip()
            if field in ticket:
                ticket[field] = datetime_now(FixedOffset(0, 'UTC'))
            ticket.save_changes()

    def get_users(self, req, users_perms_and_groups=None):
        ps = PermissionSystem(self.env)

        users = map(lambda x: x[0], self.env.get_known_users())
        groups = ps.get_groups_dict()

        if isinstance(users_perms_and_groups, str) or isinstance(users_perms_and_groups, unicode):
            users_perms_and_groups = users_perms_and_groups.split(',')
        if not isinstance(users_perms_and_groups, list):
            raise ValueError('users_perms_and_groups should be either str or list.')

        def append_owners(users_perms_and_groups):
            for user_perm_or_group in users_perms_and_groups:
                if user_perm_or_group == '$USER':
                    owners.add(req.session.sid)
                elif user_perm_or_group in users:
                    owners.add(users_perms_and_groups)
                elif user_perm_or_group == 'authenticated':
                    owners.update(set(u[0] for u in self.env.get_known_users()))
                elif user_perm_or_group.isupper():
                    perm = user_perm_or_group
                    for user in ps.get_users_with_permission(perm):
                        owners.add(user)
                elif user_perm_or_group not in groups:
                    owners.add(user_perm_or_group)
                else:
                    append_owners(groups[user_perm_or_group])

        owners = set()
        append_owners(users_perms_and_groups)

        return sorted(owners)

    def get_user_ev(self, user, start_time, end_time=None):

        sql = """SELECT sum(value) from earn_value 
                 where user = %s and time > %s"""

        if end_time is not None:
            sql += " and time < %s"

        param = (user, start_time, end_time) if end_time is not None else (user, start_time)
        result = self.env.db_query(sql, param)

        return result[0][0]

    def get_users_ev(self, users, start_time, end_time=None):

        return dict([(user, self.get_user_ev(user, start_time, end_time)) for user in users])

    def get_user_ev_detail(self, user, start_time, end_time=None):

        sql = """ SELECT e.ticket as id, e.type as ev_type, e.action, e.value, e.user, e.time, 
                  t.summary, t.type from earn_value e, ticket t 
                  where e.user = %s and t.id = e.ticket and e.time > %s"""

        if end_time is not None:
            sql += " and e.time < %s"

        param = (user, start_time, end_time) if end_time is not None else (user, start_time)
        result = self.env.db_query(sql, param)

        users = self.env.get_known_users(as_dict=True)

        for i in result:
            fullname = users.get(i[4], (None, ))[0]
            yield {'id': i[0],
                   'ev_type': i[1],
                   'action': i[2],
                   'action_name': self.config['ticket-workflow'].get(i[2] + '.name', ''),
                   'value': i[3],
                   'user': i[4],
                   'time': datetime.datetime.fromtimestamp(i[5]/1000000).strftime('%Y-%m-%d %H:%M:%S'),
                   'summary': i[6],
                   'type': i[7],
                   'fullname': fullname if fullname is not None else i[4]
                   }

    def get_users_ev_detail(self, users, start_time, end_time=None):

        return dict([(user, list(self.get_user_ev_detail(user, start_time, end_time))) for user in users])


class EarnValueMacro(WikiMacroBase):
    realm = TicketSystem.realm

    def expand_macro(self, formatter, name, content):
        evs = EarnValueSystem(self.env)
        kwargs = self._parse_arg(content)
        users = evs.get_users(formatter.req, kwargs.get('users', 'authenticated'))
        format = kwargs.get('format', 'table')
        start_time = self._parse_date(kwargs.get('start'), 0)
        end_time = self._parse_date(kwargs.get('end'), None)

        if format == 'plain':
            ev = dict([(u, evs.get_user_ev(u, start_time, end_time)) for u in users])
            tags = []
            for k, v in ev.items():
                tags.append(tag.span(k + ': ' + str(v)))
                tags.append(tag.br)
            return tag.p(*tags)

        elif format == 'table':
            evc = evs.get_users_ev_detail(users, start_time, end_time)
            rows = [tag.tr(
                tag.td(ev['action_name']),
                tag.td(ev['value']),
                tag.td(ev['fullname']),
                tag.td(ev['time']),
                tag.td(ev['summary'])
            ) for evcs in evc.values() for ev in evcs ]
            return tag.div(
                tag.table(tag.thead(
                    tag.tr(
                        tag.th('Action'),
                        tag.th('Value'),
                        tag.th('User'),
                        tag.th('Date'),
                        tag.th('Summary'), class_='trac-columns')
                ),
                tag.tbody(
                    *rows
                ), class_='listing tickets')
            )

        return None

    def _parse_arg(self, content):
        kwargs = {}
        for arg in TicketQueryMacro._comma_splitter.split(content or ''):
            arg = arg.replace(r'\,', ',')
            m = re.match(r'\s*[^=]+=', arg)
            if m:
                kw = arg[:m.end() - 1].strip()
                value = arg[m.end():]
                kwargs[kw] = value
        return kwargs

    def _parse_date(self, date_str, default):
        try:
            return to_utimestamp(datetime.strptime(date_str, '%Y-%m-%d'))
        except:
            return default