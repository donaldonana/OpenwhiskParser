from abc import ABC
from abc import abstractmethod
from typing import Optional, List, Callable, Union, Dict, Type, Tuple
import json


class State(ABC):
    def __init__(self, name: str):
        self.name = name

    @staticmethod
    def deserialize(name: str, payload: dict) -> "State":
        cls = _STATE_TYPES[payload["type"]]
        return cls.deserialize(name, payload)


class Task(State):
    def __init__(
        self, name: str, func_name: str, next: Optional[str], failure: Optional[str], web: Optional[bool] = False,
        function: Optional[str] = None, docker: Optional[str] = None, memory: Optional[str] = None, 
        pref: Optional[int] = None
    ):
        self.name = name
        self.func_name = func_name
        self.next = next
        self.failure = failure
        self.function = function
        self.docker = docker
        self.memory = memory
        self.web = web
        self.pref = pref
        
    @classmethod
    def deserialize(cls, name: str, payload: dict) -> "Task":
        return cls(
            name=name,
            func_name=payload["func_name"],
            next=payload.get("next"),
            failure=payload.get("failure"),
            function=payload.get("function"),
            docker=payload.get("docker"),
            memory=payload.get("memory"),
            web=payload.get("web", False),
            pref=payload.get("pref", 1)
            
        )


class Switch(State):
    class Case:
        def __init__(self, var: str, op: str, val: str, next: str):
            self.var = var
            self.op = op
            self.val = val
            self.next = next

        @staticmethod
        def deserialize(payload: dict) -> "Switch.Case":
            return Switch.Case(**payload)

    def __init__(self, name: str, cases: List[Case], default: Optional[str]):
        self.name = name
        self.cases = cases
        self.default = default

    @classmethod
    def deserialize(cls, name: str, payload: dict) -> "Switch":
        cases = [Switch.Case.deserialize(c) for c in payload["cases"]]

        return cls(name=name, cases=cases, default=payload["default"])


class Parallel(State):
    def __init__(self, name: str, funcs: List, next: Optional[str]):
        self.name = name
        self.funcs = funcs
        self.next = next
        self.pref = 1
         

    @classmethod
    def deserialize(cls, name: str, payload: dict) -> "Parallel":
        return cls(name=name, funcs=payload.get("parallel_functions"), next=payload.get("next"))


class Alternative(State): 
    def __init__(self, name: str, funcs: List, next: Optional[str]):
        self.name = name
        self.funcs = funcs
        self.next = next
        self.pref = None 

    @classmethod
    def deserialize(cls, name: str, payload: dict) -> "Alternative":
        return cls(name=name, funcs=payload.get("alternative_functions"), next=payload.get("next"))


class Map(State):
    def __init__(
        self,
        name: str,
        funcs: List,
        array: str,
        root: str,
        next: Optional[str],
        common_params: Optional[str],
    ):
        self.name = name
        self.funcs = funcs
        self.array = array
        self.root = root
        self.next = next
        self.common_params = common_params

    @classmethod
    def deserialize(cls, name: str, payload: dict) -> "Map":
        return cls(
            name=name,
            funcs=payload["states"],
            array=payload["array"],
            root=payload["root"],
            next=payload.get("next"),
            common_params=payload.get("common_params"),
        )


class Repeat(State):
    def __init__(self, name: str, func_name: str, count: int, next: Optional[str]):
        self.name = name
        self.func_name = func_name
        self.count = count
        self.next = next

    @classmethod
    def deserialize(cls, name: str, payload: dict) -> "Repeat":
        return cls(
            name=name,
            func_name=payload["func_name"],
            count=payload["count"],
            next=payload.get("next"),
        )


class Loop(State):
    def __init__(self, name: str, func_name: str, array: str, next: Optional[str]):
        self.name = name
        self.func_name = func_name
        self.array = array
        self.next = next

    @classmethod
    def deserialize(cls, name: str, payload: dict) -> "Loop":
        return cls(
            name=name,
            func_name=payload["func_name"],
            array=payload["array"],
            next=payload.get("next"),
        )


_STATE_TYPES: Dict[str, Type[State]] = {
    "task": Task,
    "switch": Switch,
    "map": Map,
    "repeat": Repeat,
    "loop": Loop,
    "parallel": Parallel,
    "alternative": Alternative
    
}


class Generator(ABC):
    def __init__(self, export_func: Callable[[dict], str] = json.dumps):
        self._export_func = export_func

    def parse(self, path: str):
        with open(path) as f:
            definition = json.load(f)

        self.states = {n: State.deserialize(n, s) for n, s in definition["states"].items()}
        self.root = self.states[definition["root"]]
        self.name =definition.get("name", None)

    def generate(self) -> str:
        states = list(self.states.values())
        payloads = []
        for s in states:
            obj = self.encode_state(s)
            if isinstance(obj, dict):
                payloads.append(obj)
            elif isinstance(obj, list):
                payloads += obj
            else:
                raise ValueError("Unknown encoded state returned.")

        definition = self.postprocess(payloads)

        return self._export_func(definition)

    def postprocess(self, payloads: List[dict]) -> dict:
        return payloads

    def encode_state(self, state: State) -> Union[dict, List[dict]]:
        if isinstance(state, Task):
            return self.encode_task(state)
        elif isinstance(state, Switch):
            return self.encode_switch(state)
        elif isinstance(state, Map):
            return self.encode_map(state)
        elif isinstance(state, Repeat):
            return self.encode_repeat(state)
        elif isinstance(state, Loop):
            return self.encode_loop(state)
        elif isinstance(state, Parallel):
            return self.encode_parallel(state)
        elif isinstance(state, Alternative):
            return self.encode_alternative(state)
        else:
            raise ValueError(f"Unknown state of type {type(state)}.")

    @abstractmethod
    def encode_task(self, state: Task) -> Union[dict, List[dict]]:
        pass

    @abstractmethod
    def encode_switch(self, state: Switch) -> Union[dict, List[dict]]:
        pass

    @abstractmethod
    def encode_map(self, state: Map) -> Union[dict, List[dict]]:
        pass

    @abstractmethod
    def encode_parallel(self, state: Parallel) -> Union[dict, List[dict]]:
        pass
    
    @abstractmethod
    def encode_alternative(self, state: Alternative) -> Union[dict, List[dict]]:
        pass

    def encode_repeat(self, state: Repeat) -> Union[dict, List[dict]]:
        tasks = []
        for i in range(state.count):
            name = state.name if i == 0 else f"{state.name}_{i}"
            next = state.next if i == state.count - 1 else f"{state.name}_{i+1}"
            task = Task(name, state.func_name, next, None)

            res = self.encode_task(task)
            tasks += res if isinstance(res, list) else [res]

        return tasks

    @abstractmethod
    def encode_loop(self, state: Loop) -> Union[dict, List[dict]]:
        pass
