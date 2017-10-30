class UnexpectedStatusCode(Exception):

    def __init__(self, message):
        super(Exception, self).__init__(message)


class NewRelicAlertingMissingConfVariable(Exception):

    def __init__(self, message):
        super(Exception, self).__init__(message)
