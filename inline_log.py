def log_as_dictionary(f):
    log = dict()
    for line in f.split('\n'):
        c = line.split(';')
        if len(c) <= 1:
            continue

        event = Event(c[0], c[1], c[2], c[3])
        if c[1] in log.keys():
            log[c[1]].append(event)
        else:
            log[c[1]] = [event]

    return log

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
    def __init__(self, task, case, user, date):
        self._task = task
        self._case = case
        self._user = user
        self._date = date

    def get_task(self):
        return self._task

    def get_case(self):
        return self._case

    def get_user(self):
        return self._user

    def get_date(self):
        return self._date