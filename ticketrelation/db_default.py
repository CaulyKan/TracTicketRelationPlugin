from trac.db import Table, Column

name = 'ticket_relation'
version = 2
tables = [
    Table(name, key=('a','b','relation'))[
        Column('a', type='int'),
        Column('b', type='int'),
        Column('relation', type='text'),
        Column('extra', type='text')
    ],
]
