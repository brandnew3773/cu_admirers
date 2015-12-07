import json
import re
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

postgres_mapping = {
    False: "false",
    True: "true",
    None: 'null'
}

db_mapping = postgres_mapping

# Function taken from stackoverflow:
# http://stackoverflow.com/questions/1551382/user-friendly-time-format-in-python
def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    if type(time) == unicode:
        time = parse(time)
    time = time
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days
    if day_diff < 0:
        return 'just now'

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

    def __init__(self, lhs, op, rhs, lhs_base=None):
        if type(lhs) == bool:
            self.lhs = db_mapping.get(lhs, lhs)
        else:
            self.lhs = lhs
        if type(rhs) == bool:
            self.rhs = db_mapping.get(rhs, rhs)
        else:
            self.rhs = rhs
        self.op = op
        self.lhs_base = lhs_base

    @classmethod
    def and_reduce(cls, filters):
        while len(filters) > 1:
            lhs = filters.pop()
            rhs = filters.pop()
            filters.append(And(lhs, rhs))
        return filters

    @classmethod
    def or_reduce(cls, filters):
        while len(filters) > 1:
            lhs = filters.pop()
            rhs = filters.pop()
            filters.append(Or(lhs, rhs))
        return filters

    def compose(self):
        return "%s %s %s" % (self.lhs, self.op, self.rhs)

class Equal(Filter):
    def __init__(self, lhs, rhs, lhs_base=None):
        Filter.__init__(self, lhs, "=", rhs, lhs_base)

class NotEqual(Filter):
    def __init__(self, lhs, rhs):
        Filter.__init__(self, lhs, "!=", rhs)

class And(Filter):
    def __init__(self, lhs, rhs):
        Filter.__init__(self, lhs.compose(), " and ", rhs.compose())

class Or(Filter):
    def __init__(self, lhs, rhs):
        Filter.__init__(self, lhs.compose(), " or ", rhs.compose())

class Contains(Filter):
    def __init__(self, lhs, rhs):
        Filter.__init__(self, lhs, " like ", "'%%"+rhs+"%%'")




class Table():

    connection = None

    def save(self, force_insert=False):
        values = {k:v for k,v in self.__dict__.items() if not v is None}
        if self.__dict__[self.primary_key] is None or force_insert:
            self.insert(values)
            if not force_insert:
                res = Table.connection.execute("Select LASTVAL()").fetchone()[0]
                self.__dict__[self.primary_key] = res
        else:
            self.update()


    # Sanitize and do type conversions
    def _prepare_dict(self, dict):
        for k, v in dict.items():
            if "_created" in k:
                del dict[k]
            #if type(v) == bool:
            #    dict[k] = db_mapping[v]
            elif type(v) == str or type(v) == unicode and len(v) > 0 and not v[0] == "'":
                dict[k] = "%s" % v

        return dict

    def insert(self, dict):
        dict = self._prepare_dict(dict)
        query = "INSERT INTO %s (" % self.table
        vals = []
        items = sorted(dict.keys())
        query += ", ".join(x for x in items if not x == self.primary_key)
        #vals += [x for x in items if not x == self.primary_key]
        query += ") VALUES ("
        query += ", ".join("%s" for x in items if not x == self.primary_key)
        query += ");"
        vals += [dict[x] for x in items if not x == self.primary_key]
        #print("Executing query:", query)
        return Table.connection.execute(query, vals)

    def update(self):
        query = "UPDATE %s SET " % self.table
        pd = self._prepare_dict(self.__dict__)
        query += ", ".join(k + " = %s" for k, v in pd.items() if not k == self.primary_key)
        vals = []
        for k, v in [x for x in pd.items() if not x[0] == self.primary_key]:
            vals.append(v)
        query += " WHERE " + self.primary_key + " = %s;"
        vals.append(pd[self.primary_key])
        print("Executing query:",query, vals)
        Table.connection.execute(query, vals)

    def __str__(self):
        return str(self.__dict__)

    @classmethod
    def get_all(cls, joins):
        return  cls.select([], joins)

    @classmethod
    def _convert(cls, items):
        return [cls(**x).prepare() for x in items]

    @classmethod
    def select(cls, filters, joins, cols=False):
        query = "SELECT "
        query += ", ".join(str(x) for x in cols) if cols else " * "
        query += "FROM %s" % cls.table

        for join in joins:
            query += " LEFT OUTER JOIN %s on %s.%s = %s.%s" % (join[1].table, cls.table, join[0], join[1].table, join[2])
        if filters:
            query += " WHERE "
        for filter in filters:
            query += "( %s.%s )" % (cls.table if filter.lhs_base is None else filter.lhs_base, filter.compose())
        if not query[-1] == ";":
            query += ";"
        
	#print("Executing query:", query)
        items = Table.connection.execute(query)
        return cls._convert(items)

    def prepare(self):
        return self


class Like(Table, object):
    table = "post_like"
    primary_key = "lid"

    def __init__(self, pid, sid, lid=None, response_created=None):
        self.pid = pid
        self.lid = lid
        self.sid = sid
        self.response_created = response_created


    @classmethod
    def create_table(cls, drop=True):
        if drop:
            cls.connection.execute("""DROP TABLE IF EXISTS post_like;""")
        cls.connection.execute("""CREATE TABLE IF NOT EXISTS post_like (
          lid SERIAL,
          response_created timestamp DEFAULT CURRENT_TIMESTAMP,
          pid INTEGER NOT NULL,
          sid INTEGER NOT NULL,
          FOREIGN KEY(pid) REFERENCES post(pid),
          FOREIGN KEY(sid) REFERENCES web_user(sid),
          PRIMARY KEY(lid)
        );""")


class Post(Table, object):

    table = "post"
    primary_key = "pid"

    def __init__(self, post_body, approved, poster, is_anonymous=False, allow_guesses=False,
                 tags=None, post_created=None, pid=None, like_count=0, **kwargs):
        self.post_body = post_body
        self.approved = approved
        self.poster = poster
        self.is_anonymous = is_anonymous
        self.allow_guesses = allow_guesses
        self.tags = tags
        self.pid = pid
        self.like_count = like_count
        self.post_created = post_created
        for k, v in kwargs.items():
            self.__dict__[k] = v
        super(Post, self).__init__()

    @classmethod
    def prepare_view(cls, user, posts):
        remove_keys = ["email", "password", "phone_number"]
        match_format = r"<a style='color:#00004d' href='/search/user/%s'>%s</a>"
        tag_format = r"<a style='color:#00004d' href='/search/tag/%s'>%s</a>"
        posts = posts[::-1]
        for post in posts:
            for k in remove_keys:
                post.__dict__[k] = None
            if hasattr(post, "tagged") and hasattr(user, "uni") and hasattr(post, "allow_guesses") and post.allow_guesses == 1 and post.tagged == user.uni:
                post.display_guess = True
            else:
                post.display_guess = False
            post.comments = Comment.prepare_view(user, Comment.select([Equal("pid", post.pid)], [("poster", User, "sid")]))
            body = post.post_body
            tags = re.findall(r"(#[^_\W]+)", body)
            matches = re.findall(r"(@[^_\W]+)", body)
            for tag in tags:
                body = body.replace(tag, tag_format % (tag.replace("#", ""), tag))
            for match in matches:
                body = body.replace(match, match_format % (match.replace("@", ""), match))
            post.post_created = pretty_date(post.post_created)
            post.post_body = body
            if post.poster is None:
                post.is_anonymous = True
            #else:
            #    post.is_anonymous = False
            #print "Rending Post:", post
        return posts

    @classmethod
    def create_table(cls, drop=True):
        if drop:
            cls.connection.execute("""DROP TABLE IF EXISTS post CASCADE;""")
        cls.connection.execute("""CREATE TABLE IF NOT EXISTS post (
          pid SERIAL,
          post_body text,
          like_count INTEGER DEFAULT 0,
          post_created timestamp DEFAULT CURRENT_TIMESTAMP,
          approved boolean,
          is_anonymous boolean DEFAULT true,
          tags text,
          allow_guesses boolean,
          poster integer,
          PRIMARY KEY(pid),
          FOREIGN KEY(poster) REFERENCES web_user(sid)
        );""")

    def update_save(self):
        self.save()


class Comment(Table, object):

    table = "comment"
    primary_key = "cid"

    def __init__(self, comment_body, poster, comment_created=None, pid=None, cid=None, **kwargs):
        self.comment_body = comment_body
        self.cid = cid
        self.poster = poster
        self.pid = pid
        self.comment_created = comment_created
        for k, v in kwargs.items():
            self.__dict__[k] = v
        super(Comment, self).__init__()

    def prepare(self):
        d = {"poster": (self.__dict__["poster"] == None, "Anonymous"),
            }
        for k,v in d.items():
            if k in self.__dict__ and v[0]:
                self.__dict__[k] = v[1]
        return self

    @classmethod
    def create_table(cls, drop=True):
        if drop:
            cls.connection.execute("""DROP TABLE IF EXISTS comment CASCADE;""")
        cls.connection.execute("""CREATE TABLE IF NOT EXISTS comment (
          cid SERIAL,
          comment_body text,
          pid INTEGER NOT NULL,
          comment_created timestamp DEFAULT CURRENT_TIMESTAMP,
          poster integer,
          FOREIGN KEY(pid) REFERENCES post(pid),
          FOREIGN KEY(poster) REFERENCES web_user(sid)
        );""")

    @classmethod
    def prepare_view(cls, user, comments):
        for comment in comments:
            comment.comment_created = pretty_date(comment.comment_created)
        return comments

class GuessSetting(Table, object):
    table = "guess_setting"
    primary_key = "gsid"

    def __init__(self, pid, tagged=None, num_guesses=3, remaining=3, matched=False, gsid=None):
        self.pid = pid
        self.gsid = gsid
        self.tagged = tagged
        self.num_guesses = num_guesses
        self.remaining = remaining
        self.matched = matched

    @classmethod
    def create_table(cls, drop=True):
        if drop:
            cls.connection.execute("""DROP TABLE IF EXISTS guess_setting CASCADE;""")
        cls.connection.execute("""CREATE TABLE IF NOT EXISTS guess_setting (
          gsid SERIAL,
          pid INTEGER NOT NULL,
          tagged TEXT,
          num_guesses INTEGER,
          remaining INTEGER,
          matched BOOLEAN,
          PRIMARY KEY(gsid),
          FOREIGN KEY(pid) REFERENCES post(pid) ON DELETE CASCADE
        );""")

class User(Table, object):

    table = "web_user"
    primary_key = "sid"

    def __init__(self, first_name, last_name, email, uni=None, sid=None, password = None,
                 email_verified = False):
        self.sid = sid
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.email_verified = email_verified
        self.password = password
        self.uni = uni
        super(User, self).__init__()

    def is_active(self):
        return True

    def get_id(self):
        return self.email

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False

    def set_password(self, raw_password):
        hash = sha256_crypt.encrypt(raw_password)
        self.password = hash

    def check_password(self, raw_password):
        if sha256_crypt.verify(raw_password, self.password):
            self.authenticated = True
            return True
        return False

    @classmethod
    def create_table(cls, drop=True):
        if drop:
            cls.connection.execute("""DROP TABLE IF EXISTS web_user CASCADE;""")
        cls.connection.execute("""CREATE TABLE IF NOT EXISTS web_user (
        sid SERIAL,
        first_name text,
        last_name text,
        email text NOT NULL,
        uni text NOT NULL,
        email_verified boolean,
        password text NOT NULL,
        PRIMARY KEY(sid)
       );""")










