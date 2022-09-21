import xml.etree.ElementTree as ET
from datetime import datetime

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
