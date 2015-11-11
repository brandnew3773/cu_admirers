from sqlalchemy import *
from datetime import datetime

DATABASEURI = "sqlite:///test.db"

engine = create_engine(DATABASEURI)
conn = engine.connect()


sqlite_mapping = {
    False: '0',
    True: '1',
    None: 'null'
}

db_mapping = sqlite_mapping



class Filter():

    def __init__(self, lhs, op, rhs):
        self.lhs = db_mapping.get(lhs, lhs)
        self.rhs = db_mapping.get(rhs, rhs)
        self.op = op

    def compose(self):
        return "(%s %s %s)" % (self.lhs, self.op, self.rhs)

class Equal(Filter):
    def __init__(self, lhs, rhs):
        Filter.__init__(self, lhs, "=", rhs)

class NotEqual(Filter):
    def __init__(self, lhs, rhs):
        Filter.__init__(self, lhs, "!=", rhs)

class And(Filter):
    def __init__(self, lhs, rhs):
        Filter.__init__(self, lhs.compose(), " and ", rhs.compose())

class Or(Filter):
    def __init__(self, lhs, rhs):
        Filter.__init__(self, lhs.compose(), " or ", rhs.compose())



class Table():

    def save(self):
        values = {k:v for k,v in self.__dict__.items() if not v is None}
        if self.__dict__[self.primary_key] is None:
            self.insert(values)
            res = conn.execute("Select last_insert_rowid()").fetchone()[0]
            self.__dict__[self.primary_key] = res
        else:
            self.update()

    def _prepare_dict(self, dict):
        for k, v in dict.items():
            if v in db_mapping.keys():
                dict[k] = db_mapping[v]
            elif type(v) == str and not v[0] == "'":
                dict[k] = "\'%s\'" % v
        return dict

    def insert(self, dict):
        dict = self._prepare_dict(dict)
        query = "INSERT INTO %s (" % str(self.table)
        items = sorted(dict.keys())
        query += ", ".join(str(x) for x in items if not x == self.primary_key)
        query += ") VALUES ("
        query += ", ".join(str(dict[x]) for x in items if not x == self.primary_key)
        query += ");"
        return conn.execute(query)

    def update(self):
        query = "UPDATE %s SET " % self.table
        pd = self._prepare_dict(self.__dict__)
        query += ", ".join(" %s = %s" % (k, v) for k, v in pd.items() if not k == self.primary_key)
        query += " WHERE %s = %s;" % (self.primary_key, pd[self.primary_key])
        conn.execute(query)

    def __str__(self):
        return str(self.__dict__)

    #def __setattr__(self, key, value):
    #    self.dict[key] = value


    @classmethod
    def get_all(cls):
        return  cls.select([], [])

    @classmethod
    def _convert(cls, items):
        return [cls(**x) for x in items]

    @classmethod
    def select(cls, filters, cols=False):
        query = "SELECT "
        query += ", ".join(str(x) for x in cols) if cols else " * "
        query += "FROM %s WHERE" % cls.table if filters else "FROM %s;" % cls.table
        for filter in filters:
            query += " %s " % filter.compose()
        items = conn.execute(query)
        return cls._convert(items)

    #@classmethod
    #def create_table(cls):




#def to_table(cls):
#    cls.primary_key = cls.primary_key
#    cls.__name__ = cls.table_name


class Post(Table, object):

    table = "post"
    primary_key = "pid"

    def __init__(self, post_body, approved, poster, lid, post_created=None, pid=None):
        self.post_body = post_body
        self.approved = approved
        self.poster = poster
        self.lid = lid
        self.pid = pid
        self.post_created = post_created
        super(Post, self).__init__()



conn.execute("""DROP TABLE IF EXISTS post;""")
conn.execute("""CREATE TABLE IF NOT EXISTS post (
  pid INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
  post_body text,
  post_created timestamp,
  approved boolean,
  poster integer,
  lid integer
);""")


p = Post("hello world", False, 1, 2)
p.save()
p.post_body = "goodbye"
p.save()


objects = Post.get_all()



x = Post.select([And(Equal("poster", 1), Equal("approved", False))])

print(str(x[0]))







