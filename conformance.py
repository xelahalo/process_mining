import xml.etree.ElementTree as ET
from datetime import datetime
import uuid
from itertools import chain, combinations

def fitness_token_replay(log, mined_model):
    trace_properties = get_trace_properties(log)
    token_replay(mined_model, trace_properties)
    return calculate_fitness(trace_properties)

def get_trace_properties(log):
    properties = set()

    for events in log.values():
        trace = []
        for event in events:
            trace.append(event)

        trace_props = TraceProperties(trace)

        if trace_props in properties:
            for prop in properties:
                if prop == trace_props:
                    prop.set_occurrences(prop.get_occurrences() + 1)
        else:
            properties.add(trace_props)

    return properties         
    
def token_replay(model, trace_properties):
    for prop in trace_properties:
        p = 0
        c = 0
        m = 0
        r = 0

        model.add_marking(0)
        p += 1

        for event in prop.get_trace():
            transition_id = model.transition_name_to_id(event.get_task())

            dot_t = model.dot_t(transition_id)
            t_dot = model.t_dot(transition_id)

            if not model.is_enabled(transition_id):
                for place in dot_t:
                    if not place.has_tokens():
                        place.increment_tokens()
                        m += 1

            model.fire_transition(transition_id)
            c += len(dot_t)
            p += len(t_dot)
            if p + m < c and c < m:
                raise Exception('Violation')

        found = model.consume_end_place_token()
        c += 1
        if not found:
            m += 1
        
        r += model.get_remaining_tokens()
        model.clear_tokens()

        prop.set_after_replay(m,c,r,p)
        if (p + m - c) != r:
            raise Exception('Violation')

def calculate_fitness(trace_properties):
    nm = 0
    nc = 0
    nr = 0
    np = 0
    for prop in trace_properties:
        nm += prop.get_occurrences() * prop.get_missing()
        nc += prop.get_occurrences() * prop.get_consumed()
        nr += prop.get_occurrences() * prop.get_remaining()
        np += prop.get_occurrences() * prop.get_produced()

    a = (1/2*(1 - nm/nc))+(1/2*(1 - nr/np))
    return a

class TraceProperties():
    def __init__(self, trace,):
        self._trace = trace
        self._occurrences = 1
        self._missing = 0
        self._consumed = 0
        self._remaining = 0
        self._produced = 0

    def set_occurrences(self, n):
        self._occurrences = n

    def get_occurrences(self):
        return self._occurrences

    def get_missing(self):
        return self._missing

    def get_consumed(self):
        return self._consumed

    def get_remaining(self):
        return self._remaining

    def get_produced(self):
        return self._produced

    def set_after_replay(self, m,c,r,p):
        self._missing = m
        self._consumed = c
        self._remaining = r
        self._produced = p

    def get_trace(self):
        return self._trace

    def __hash__(self):
        return hash(tuple(self._trace))

    def __eq__(self, other):
        if isinstance(other, TraceProperties):
            return self._trace == other.get_trace()

def alpha(log):
    wf_net = WorkflowNet(log)
    wf_net.omit_duplicate_traces()
    wf_net.init_transition_sets()
    wf_net.get_ordering_relations()
    wf_net.init_places()
    wf_net.init_flow_relations()
    wf_net.build_petri_net()
    
    return wf_net.get_petri_net()

class WorkflowNet():
    def __init__(self, log):
        self._log = log
        self.T_W = set()
        self.T_I = set()
        self.T_O = set()
        self.X_W = set()
        self.Y_W = set()
        self.P_W = set()
        self.F_W = set()
        self._direct_successions = set()
        self._choices = set()
        self._causals = set()
        self._petri_net = None
    
    def omit_duplicate_traces(self):
        hashset = set()
        new_log = dict()

        for case, events in self._log.items():
            hashvalue = ""
            for event in events:
                hashvalue = hash((hashvalue, event.__hash__()))

            if hashvalue in hashset:
                continue

            hashset.add(hashvalue)
            new_log[case] = events

        self._log = new_log
    
    def get_ordering_relations(self):
        self._get_direct_successions()
        self._get_choices()
        self._get_causals()

    def init_transition_sets(self):
        all_events = set()
        initial_events = set()
        end_events = set()
        for events in self._log.values():
            initial_events.add(events[0])
            end_events.add(events[-1])
            all_events = all_events.union(set(event for event in events))
        
        self.T_W = self.T_W.union(set([Transition.from_event(event) for event in all_events]))

        for T in self.T_W:
            for initial in initial_events:
                if initial.get_task() == T.get_name():
                    self.T_I.add(T)

            for end in end_events:
                if end.get_task() == T.get_name():
                    self.T_O.add(T)
            
    def init_places(self):
        if len(self.T_W) <= 0:
            return
        
        T_W_subsets = self._get_all_nonempty_subsets(self.T_W)

        for A in T_W_subsets:
            for B in T_W_subsets:
                if self._are_X_W_elements(A, B):
                    self.X_W.add((A, B))
        
        self.Y_W = self.X_W.copy()
        for A, B in self.X_W:
            for A_prime, B_prime in self.X_W:
                if (A, B) != (A_prime, B_prime) and set(A).issubset(A_prime) and set(B).issubset(B_prime):
                    self.Y_W.discard((A, B))

        self.P_W.add(Place(0, 0, None, self.T_I))
        i = 1
        for A, B in self.Y_W:
            self.P_W.add(Place(i, 0, A, B))
            i+=1
        self.P_W.add(Place(i, 0, self.T_O, None))

    def init_flow_relations(self):
        for place in self.P_W:
            A = place.get_A()
            B = place.get_B()

            for transition in A:
                self.F_W.add(Edge(transition.get_id(), place.get_id()))

            for transition in B:
                self.F_W.add(Edge(place.get_id(), transition.get_id()))

    def build_petri_net(self):
        self._petri_net = PetriNet(self.P_W, self.T_W, self.F_W)
    
    def get_petri_net(self):
        return self._petri_net

    def _get_all_nonempty_subsets(self, iterable):
        s = list(iterable)
        return list(chain.from_iterable(combinations(s, r) for r in range(1, len(s)+1)))

    def _get_direct_successions(self):
        for events in self._log.values():
            prev_transition = None
            for event in events:
                transition = None
                # Don't want to recreate transition so, we find it within the existing ones
                for t in self.T_W:
                    if t.get_name() == event.get_task():
                        transition = t

                if prev_transition is not None:
                    self._direct_successions.add((prev_transition, transition))

                prev_transition = transition

    def _get_causals(self):
        for succession in self._direct_successions:
            if (succession[1], succession[0]) not in self._direct_successions:
                self._causals.add(succession)

    def _get_choices(self):
        for outer_transition in self.T_W:
            for inner_transition in self.T_W:
                left_right_relation = (outer_transition, inner_transition)
                right_left_relation = (inner_transition, outer_transition)

                if left_right_relation in self._direct_successions or right_left_relation in self._direct_successions:
                    continue
                
                self._choices.add(left_right_relation)

    def _are_X_W_elements(self, A, B):
        if len(A) <= 0:
            return False

        if len(B) <= 0:
            return False
        
        for a_1 in A:
            for a_2 in A:
                if (a_1, a_2) not in self._choices:
                    return False
            
            for b in B:
                if (a_1, b) not in self._causals:
                    return False

        for b_1 in B:
            for b_2 in B:
                if (b_1, b_2) not in self._choices:
                    return False
        
        return True

class PetriNet():
    def __init__(self, places=None, transitions=None, edges=None):
        self._places = set() if places is None else places
        self._transitions = set() if transitions is None else transitions
        self._edges = set() if edges is None else edges

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

    def get_remaining_tokens(self):
        r = 0
        for place in self._places:
            if place.has_tokens():
                r += place.get_tokens()

        return r

    def is_enabled(self, transition):
        for p in self.dot_t(transition):
            if p.has_tokens():
                continue
            else:
                return False

        return True

    def get_enabled_transitions(self):
        transitions = []
        for transition in self._transitions:
            if self.is_enabled(transition.get_id()):
                transitions.append(transition)

        return transitions

    def add_marking(self, place_id):
        for place in self._places:
            if place.get_id() == place_id:
                place.increment_tokens()

    def fire_transition(self, transition):
        if not self.is_enabled(transition):
            return

        dot_t = self.dot_t(transition)
        t_dot = self.t_dot(transition)

        for place in dot_t:
            place.decrement_tokens()

        for place in t_dot:
            place.increment_tokens()

    def transition_name_to_id(self, name):
        for transition in self._transitions:
            if transition.get_name() == name:
                return transition.get_id()
        
        return None

    def clear_tokens(self):
        for place in self._places:
            place.clear_tokens()

    def consume_end_place_token(self):
        found = False
        for place in self._places:
            is_end = True
            for edge in self._edges:
                if edge.is_source(place.get_id()):
                    is_end = False

            if is_end and place.has_tokens():
                found = True
                place.decrement_tokens()

        return found

    def dot_t(self, t):
        dot_t = set()
        for edge in self._edges:
            if edge.is_target(t):
                place = self._get_place_by_id(edge.get_source())
                dot_t.add(place)

        return dot_t

    def t_dot(self, t):
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
    def __init__(self, id, num_of_tokens=0, A=None, B=None):
        self._id = id
        self._num_of_tokens = num_of_tokens
        self._A = set() if A is None else A
        self._B = set() if B is None else B

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

    def clear_tokens(self):
        self._num_of_tokens = 0

    def get_A(self):
        return self._A
    
    def get_B(self):
        return self._B

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
            return self._id == self._id

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

    def __hash__(self):
        return hash(self._name)

    def __eq__(self, other):
        if isinstance(other, Event):
            return self._name == other._name