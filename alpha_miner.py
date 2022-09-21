import xml.etree.ElementTree as ET
from datetime import datetime
import uuid
from itertools import chain, combinations

def alpha(log):
    wf_net = WorkflowNet(log)
    
class WorkflowNet():
    def __init__(self, log):
        self._log = log
        self.T_W = set()
        self.T_I = set()
        self.T_O = set()
        self._petri_net = None
                
    def init_transition_sets(self):
        for tasks in self._log.values():
            self.T_W.union(set([Transition.from_event(task) for task in tasks]))
            self.T_I.union(Transition.from_event(tasks[0]))
            self.T_O.union(Transition.from_event(tasks[-1]))
            
    def init_places(self):
        if len(self.T_W) <= 0:
            return
        
        T_W_subsets = self._get_all_nonempty_subsets(self.T_W)
        A, B = T_W_subsets
        
    def direct_succesions(self):
        pass
    
    def causality(self):
        pass
    
    def paralell(self):
        pass
    
    def choice(self):
        pass
            
    def build_petrni_net(self):
        pass
    
    def get_petrni_net(self):
        return self._petri_net

    def _get_all_nonempty_subsets(self, iterable):
        s = list(iterable)
        return list(chain.from_iterable(combinations(s, r) for r in range(len(s)+1)))
        

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

    def transition_name_to_id(self, name):
        for transition in self._transitions:
            if transition.get_name() == name:
                return transition.get_id()
        
        return None

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

    @classmethod
    def from_event(cls, event):
        name = event.get_task()
        id = uuid.uuid4()
        return cls(name, id)

    def get_id(self):
        return self._id
    
    def get_name(self):
        return self._name

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

def read_from_file(path):
    tree = ET.parse(path)
    root = tree.getroot()

    cases = dict()

    for trace in root:
        if not trace.tag.endswith('trace'):
            continue

        case = None
        for event in trace:
            if event.tag.endswith('string'):
                case = event.get('value')
                if case not in cases.keys():
                    cases[case] = []
                continue

            event_wrapper = Event(case)

            for child in event:
                if child.get('key') == "concept:name":
                    event_wrapper.set_name(child.get('value'))
                elif child.tag.endswith('date'):
                    time = datetime.fromisoformat(child.get('value'))
                    time = time.replace(tzinfo=None)
                    event_wrapper.set_time(time)
                elif child.tag.endswith('int'):
                    event_wrapper.set_cost(int(child.get('value')))
                else:
                    event_wrapper.add_resource(child.get('value'))

            cases[case].append(event_wrapper)

    return cases

def dependency_graph(log):
    dg = dict()
    for _, events in log.items():
        prev_task = None
        for event in events:
            task = event.get_task()
            if task not in dg.keys():
                dg[task] = dict()

            if prev_task is not None:
                if task not in dg[prev_task].keys():
                    dg[prev_task][task] = 1
                else:
                    dg[prev_task][task] += 1

            prev_task = task

    return dg

class Event:
    def __init__(self, case):
        self._case = case
        self._resources = []

    def set_name(self, name):
        self._name = name
        
    def add_resource(self, resource):
        self._resources.append(resource)

    def set_time(self, time):
        self._time = time
    
    def set_cost(self, cost):
        self._cost = cost

    def get_task(self):
        return self._name

    def __getitem__(self, key):
        if key == 'concept:name':
            return self._name
        elif key == 'time:timestamp':
            return self._time
        elif key == 'cost':
            return self._cost
        else:
            return self._resources[0]
