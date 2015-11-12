from sqlalchemy import *
from datetime import datetime
from passlib.hash import sha256_crypt
from datetime import datetime, timedelta
from dateutil.parser import parse

#DATABASEURI = "sqlite:///test.db"

#engine = create_engine(DATABASEURI)
#conn = engine.connect()


sqlite_mapping = {
    False: '0',
    True: '1',
    None: 'null'
}

db_mapping = sqlite_mapping

# Function taken from stackoverflow:
# http://stackoverflow.com/questions/1551382/user-friendly-time-format-in-python
def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    time = time - timedelta(hours=5)
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days
    print(day_diff)
    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(second_diff / 60) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(second_diff / 3600) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff / 7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff / 30) + " months ago"
    return str(day_diff / 365) + " years ago"


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

    def save(self, conn):
        values = {k:v for k,v in self.__dict__.items() if not v is None}
        if self.__dict__[self.primary_key] is None:
            self.insert(values, conn)
            res = conn.execute("Select last_insert_rowid()").fetchone()[0]
            self.__dict__[self.primary_key] = res
        else:
            self.update(conn)

    def _prepare_dict(self, dict):
        for k, v in dict.items():
            if v in db_mapping.keys():
                dict[k] = db_mapping[v]
            elif type(v) == str or type(v) == unicode and not v[0] == "'":
                dict[k] = "\'%s\'" % v
        return dict

    def insert(self, dict, conn):
        dict = self._prepare_dict(dict)
        query = "INSERT INTO %s (" % str(self.table)
        items = sorted(dict.keys())
        query += ", ".join(str(x) for x in items if not x == self.primary_key)
        query += ") VALUES ("
        query += ", ".join(str(dict[x]) for x in items if not x == self.primary_key)
        query += ");"
        return conn.execute(query)

    def update(self, conn):
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
    def get_all(cls, conn):
        return  cls.select([], conn)

    @classmethod
    def _convert(cls, items):
        return [cls(**x).prepare() for x in items]

    @classmethod
    def select(cls, filters, conn, cols=False):
        query = "SELECT "
        query += ", ".join(str(x) for x in cols) if cols else " * "
        query += "FROM %s WHERE" % cls.table if filters else "FROM %s;" % cls.table
        for filter in filters:
            query += " %s " % filter.compose()
        items = conn.execute(query)
        return cls._convert(items)

    def prepare(self):
        return self
    #@classmethod
    #def create_table(cls):




#def to_table(cls):
#    cls.primary_key = cls.primary_key
#    cls.__name__ = cls.table_name


class Post(Table, object):

    table = "post"
    primary_key = "pid"

    def __init__(self, post_body, approved, poster, lid, allow_guesses=False, post_created=None, pid=None):
        self.post_body = post_body
        self.approved = approved
        self.poster = poster
        self.lid = lid
        self.allow_guesses = allow_guesses
        self.pid = pid
        self.post_created = post_created
        super(Post, self).__init__()

    def prepare(self):
        d = {"poster": (self.__dict__["poster"] == None, "Anonymous"),
            }
        for k,v in d.items():
            if k in self.__dict__ and v[0]:
                self.__dict__[k] = v[1]
                print("preparing")
                print(self.__dict__[k])
        if self.__dict__["post_created"] != None:
            new_date = pretty_date(parse(self.__dict__["post_created"]))
            self.__dict__["post_created"] = new_date
        return self

    @classmethod
    def create_table(cls, conn, drop=True):
        if drop:
            conn.execute("""DROP TABLE IF EXISTS post;""")
        conn.execute("""CREATE TABLE IF NOT EXISTS post (
          pid INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
          post_body text,
          post_created timestamp DEFAULT CURRENT_TIMESTAMP,
          approved boolean,
          allow_guesses boolean,
          poster integer,
          lid integer
        );""")

class User(Table, object):

    table = "web_user"
    primary_key = "sid"

    def __init__(self, first_name, last_name, email, sid=None, password = None,
                 phone_number = None, email_verified = False, uni_name=None):
        self.sid = sid
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.email_verified = email_verified
        self.phone_number = phone_number
        self.password = password
        self.uni_name = uni_name
        #self.authenticated = self.check_password(password)
        super(User, self).__init__()

    def is_active(self):
        """True, as all users are active."""
        return True

    def get_id(self):
        """Return the email address to satisfy Flask-Login's requirements."""
        return self.email

    def is_authenticated(self):
        """Return True if the user is authenticated."""
        return True

    def is_anonymous(self):
        """False, as anonymous users aren't supported."""
        return False

    def set_password(self, raw_password):
        hash = sha256_crypt.encrypt(raw_password)
        self.password = hash

    def check_password(self, raw_password):
        if sha256_crypt.verify(raw_password, self.password):
            self.authenticated = True
            return True
        return False



#conn.execute("""DROP TABLE IF EXISTS post;""")
#conn.execute("""CREATE TABLE IF NOT EXISTS post (
#  pid INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
#  post_body text,
#  post_created timestamp,
#  approved boolean,
#  poster integer,
#  lid integer
#);""")


# conn.execute("""DROP TABLE IF EXISTS web_user;""")
# conn.execute("""CREATE TABLE IF NOT EXISTS web_user (
#   sid INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
#   first_name text,
#   last_name text,
#   email text,
#   email_verified boolean,
#   phone_number text,
#   password text,
#   uni_name text
# );""")

#p = Post("hello world", False, 1, 2)
#p.save()
#p.post_body = "goodbye"
#p.save()


#objects = Post.get_all()



#x = Post.select([And(Equal("poster", 1), Equal("approved", False))])

#print(str(x[0]))







