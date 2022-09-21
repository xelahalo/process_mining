class PetriNet():
    def __init__(self):
        self._places = set()
        self._transitions = set()
        self._edges = set()

    def add_place(self, name):
        self._places.add(Place(name))
        return self

    def add_transition(self, name, id):
        self._transitions.add(Transition(name, id))
        return self

    def add_edge(self, source, target):
        self._edges.add(Edge(source, target))
        return self

    def get_tokens(self, id):
        return self._get_place_by_id(id).get_tokens()

    def is_enabled(self, transition):
        for p in self._dot_t(transition):
            if p.has_tokens():
                continue
            else:
                return False

        return True

    def add_marking(self, place_id):
        for place in self._places:
            if place.get_id() == place_id:
                place.increment_tokens()

    def fire_transition(self, transition):
        if not self.is_enabled(transition):
            return

        dot_t = self._dot_t(transition)
        t_dot = self._t_dot(transition)

        for place in dot_t:
            place.decrement_tokens()

        for place in t_dot:
            place.increment_tokens()


    def _dot_t(self, t):
        dot_t = set()
        for edge in self._edges:
            if edge.is_target(t):
                place = self._get_place_by_id(edge.get_source())
                dot_t.add(place)

        return dot_t

    def _t_dot(self, t):
        t_dot = set()
        for edge in self._edges:
            if edge.is_source(t):
                place = self._get_place_by_id(edge.get_target())
                t_dot.add(place)

        return t_dot

    def _get_place_by_id(self, id):
        for place in self._places:
            if place.get_id() == id:
                return place

        return None

class Place():
    def __init__(self, id, num_of_tokens=0):
        self._id = id
        self._num_of_tokens = num_of_tokens

    def get_id(self):
        return self._id

    def has_tokens(self):
        return self._num_of_tokens > 0

    def get_tokens(self):
        return self._num_of_tokens

    def increment_tokens(self):
        self._num_of_tokens += 1

    def decrement_tokens(self):
        if self._num_of_tokens <= 0:
            return
        
        self._num_of_tokens -= 1

    def __hash__(self):
        return hash(self._id)

    def __eq__(self, other):
        if isinstance(other, Place):
            return self._id == other._id

class Transition():
    def __init__(self, name, id):
        self._name = name
        self._id = id

    def __hash__(self):
        return hash(self._id)

    def __eq__(self, other):
        if isinstance(other, Transition):
            return self._id == other._id

class Edge():
    def __init__(self, left, right):
        self._source = left
        self._target = right

    def is_target(self, target):
        return self._target == target

    def is_source(self, source):
        return self._source == source

    def get_target(self):
        return self._target

    def get_source(self):
        return self._source

    def __hash__(self):
        return hash((self._source, self._target))

    def __eq__(self, other):
        if isinstance(other, Edge):
            return self._source == other._source and self._target == other._target