from yarl import URL


class Book:
    def __init__(self, title, author, publishing_issue, marc_no, borrowed=True):
        self.title = title
        self.author = author
        self.publishing_issue = publishing_issue
        self.marc_no = marc_no
        self.borrowed = borrowed

    def __repr__(self):
        return 'Book Object ({title}) ({marc_no}) ({borrowed})'.format(title=self.title, marc_no=self.marc_no,
                                                                       borrowed='不可借' if self.borrowed else '可借')

    def __str__(self):
        return '[{title} {author} {publishing_issue} {borrowed}]'.format(title=self.title, author=self.author,
                                                                         publishing_issue=self.publishing_issue,
                                                                         borrowed='不可借' if self.borrowed else '可借')

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError
        if self.marc_no == other.marc_no:
            return True
        return False

    @classmethod
    def serialize(cls, obj):
        if not isinstance(obj, cls):
            raise TypeError
        return obj.__dict__

    @classmethod
    def deserialization(cls, d):
        return cls(d['title'], d['author'], d['publishing_issue'], d['marc_no'], d['borrowed'])

    def get_detail_page_url(self):
        return URL('http://210.32.33.91:8080/opac/item.php').with_query(marc_no=self.marc_no)

    def get_ajax_page_url(self):
        return URL('http://210.32.33.91:8080/opac/ajax_item.php').with_query({'marc_no': self.marc_no})

    def can_be_borrowed(self):
        return '不可借' if self.borrowed else '可借'
