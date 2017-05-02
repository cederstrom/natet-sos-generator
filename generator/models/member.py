class Member:
    id = 0

    def __init__(self, first_name="", last_name="", proportion=100, family=0, sponsor_for_family=None):
        self.first_name = first_name
        self.last_name = last_name
        self.proportion = proportion
        self.family = family
        self.sponsor_for_family = sponsor_for_family

    @property
    def name(self):
        return self.first_name + " " + self.last_name

    @property
    def is_sponsor(self):
        return self.sponsor_for_family is not None
