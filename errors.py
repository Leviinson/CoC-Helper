'''Contains custom errors classes.'''

class BadRequestError(Exception):
    pass

class ClanWarEndedError(Exception):
    pass

class ClanNotFoundError(Exception):
    pass