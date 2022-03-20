from src.primitives import *


class ICardOperations:
    """ Common interface for card operation classes. Maybe one day we will trade using more banks. """

    def get_operations(self, from_date=None, to_date=None, amount=100) -> [FiatOperation]:
        pass

    def send(self, card, amount, currency='RUB') -> None:
        pass
