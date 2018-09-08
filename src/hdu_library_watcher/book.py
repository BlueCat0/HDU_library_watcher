from yarl import URL


class Book:
    def __init__(self, title: str, author: str, publisher: str, publish_date: str, call_no: str, marc_no: str,
                 state: bool):
        self.title = title
        self.author = author
        self.publisher = publisher
        self.publish_date = publish_date
        self.call_no = call_no
        self.marc_no = marc_no
        self.state = state

    def __repr__(self):
        return '<Book Object {title} {borrowed}>'.format(title=self.title, borrowed=self.get_state())

    def __str__(self):
        return '{state} {title} {author} {publisher} {publish_date} {call_no}'.format(state=self.get_state(),
                                                                                      title=self.title,
                                                                                      author=self.author,
                                                                                      publisher=self.publisher,
                                                                                      publish_date=self.publish_date
                                                                                      , call_no=self.call_no)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError(other, self.__class__)
        if self.call_no == other.call_no:
            return True
        return False

    def __hash__(self):
        return hash(self.call_no)

    @classmethod
    def serialize(cls, obj):
        if not isinstance(obj, cls):
            raise TypeError
        return obj.__dict__

    @classmethod
    def deserialization(cls, d: dict):
        if 'title' in d.keys():
            return cls(title=d['title'], author=d['author'], publisher=d['publisher'],
                       publish_date=d['publish_date'], call_no=d['call_no'], marc_no=d['marc_no'], state=d['state'])
        else:
            return d

    def get_state(self):
        return '不可借' if not self.state else '可借'

    def get_detail_page_url(self):
        return URL('http://210.32.33.91:8080/opac/item.php').with_query(marc_no=self.marc_no)
