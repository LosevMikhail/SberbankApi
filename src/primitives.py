""" Common project data structures """
import json
import re


class Person:
    """ Does not contain card number since it is not required for checking who sent the money """
    def __init__(self, definition: str):
        self._definition = definition

    # todo comparison methods

    @staticmethod
    def create(definition: str, mode='sber'):
        try:
            person = Person(definition)
            # @todo handle the incoming case
            [person._name, person._patronymic, person._surname] = re.findall(r'[а-яА-ЯёЁ]+', definition)
            [person._card] = re.findall(r'\d{4}\s\d{2}\*{2}\s\*{4}\s\d{4}', definition)
            return person
        except Exception:
            return None

    def __repr__(self):
        return json.dumps(self, default=lambda o: o.__dict__, ensure_ascii=False)

    def get_definition(self):
        return self._definition


class FiatOperation:
    """ Bank card operation info """

    def __init__(self, person: Person, amount: float):
        self._person = person
        self._amount = amount

    @staticmethod
    def create(definition: str, amount: float):
        person = Person.create(definition)
        if person is None:
            return None
        operation = FiatOperation(person, amount)
        return operation

    def get_person(self):
        return self._person

    def get_amount(self):
        return self._amount

    def __repr__(self):
        return json.dumps(self, default=lambda o: o.__dict__, ensure_ascii=False)
