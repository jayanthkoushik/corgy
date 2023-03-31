# Global classes for pickle tests.
class PklTestA:
    def __init__(self, x: int):
        self.x = x

    def __eq__(self, other):
        return isinstance(other, self.__class__) and other.x == self.x

    def __hash__(self):
        return hash(self.x)


class PklTestB(PklTestA):
    ...


class PklTestC(PklTestA):
    ...
