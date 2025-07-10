from typing import Dict, List, Union, Any
import numbers
import uuid
from itertools import product
import json
import os
import yaml
from pathlib import Path
import sys


from fsm import Generator, State, Task, Switch, Map, Repeat, Loop, Parallel, Alternative


def list2dict(lst, key):
    dct = {}
    for item in lst:
        if isinstance(item, list):
            r = list2dict(item, key)
            dct.update(r)
        else:
            keyvalue = item[key]
            del item[key]
            dct[keyvalue] = item
    return dct


class OWKGenerator(Generator):
    def __init__(self):
        super().__init__()
        self.sequences = {}
        self.idseq = 0
        self.idpar = 0
        
        
    def build_sequences(self, root: State, states: dict) -> list:
        sequences = []
        roots = []
        
        if isinstance(root, Task):
            roots.append([root])
        else:
            for subworkflow in root.funcs:
                roots.append([subworkflow])
        
        for seq in roots:
            current = seq[0]
            if  current.next: 
                subseq = self.build_sequences(states[current.next], self.states)
                result = [x + y for x in [seq] for y in subseq]
                for item in result:
                    sequences.append(item)
            else:
                sequences.append(seq)

        return sequences
    
    
    def postparallel(self, sequences : list, state:Parallel):
        states = {}
        finalseq = [sum(combo, []) for combo in product(*sequences)]
        
        for i, seq in enumerate(finalseq):
            pref = 0
            for item in seq: 
                pref += self.sequences[str(item)]["annotations"]["pref"]
                
            # Create an action that runs these branches in parallel
            name = f"A{self.idpar+1}"
            action = {
                "type" : "task",
                "function": f"action/{name}.py",
                "func_name": name,
                "next" : state.next,
                "pref" : pref
            }
            states[f"{name}"] = State.deserialize(name, action)
            self.states.update(states)
            
            # Create the Python file contents for the parallel action
            with open("template.py", "r") as template_file:
                template_code = template_file.read()

            replacements = {
                "action_args.items()": str(seq),
                "main(args, action_args)": "main(args)",
                "{namespace}/{package_name}": "guest/default"
            }

            for old, new in replacements.items():
                template_code = template_code.replace(old, new)

            # Make sure "action" folder already exist
            os.makedirs("action", exist_ok=True)
                    
            with open(f"action/{name}.py", "w") as f:
                f.write(template_code)
            
            self.idpar += 1
        
        functions = [self.encode_state(t) for t in states.values()]
        state.funcs = [t for t in states.values()]
        
        return functions   

    def postprocess(self, payloads: List[dict]) -> dict:
        state_payloads = list2dict(payloads, "Name")
        pack_name = "default"
        
        if self.name:
            name = self.name
        else:
            name = "Test"
        
        sequences = self.build_sequences(self.root, self.states) # Build the final sequence.s 
        for i, seq in enumerate(sequences):
            actions = []
            pref = 1
            
            for item in seq: 
                actions.append(item.name)
                pref = pref*item.pref
            
            seq = {
                f"{name}.S{i+1}" : {
                    "annotations": {"pref" : pref},
                    "web" : True,
                    "actions" : ",".join(actions)
                    }
                }
            
            self.sequences.update(seq)
            
        definition = {
            "packages": {
                f"{pack_name}" : {
                    "actions" : state_payloads,
                    "sequences" : self.sequences
                }
            }
        }
        
        # print(f"workflow definition: ")
        # print(json.dumps(definition, default=lambda o: "<not serializable>", indent=2))
        
        return definition


    def encode_task(self, state: Task) -> Union[dict, List[dict]]:
        payload: Dict[str, Any] = {
            "Name": state.func_name,
            "annotations" : {
                "pref" : state.pref
            }
        }
        
        if state.function :
            payload["function"] =  state.function 
        else:
            raise ValueError(f"Please you need to provide the path to code source")
            
        if state.web : 
            payload["web"] =  state.web 
        
        if state.docker : 
            payload["docker"] =  state.docker 
            
        if state.memory : 
            payload["limits"] = {
                "memorySize" : state.memory
            }
            
        return payload
    

    def encode_parallel(self, state: Parallel) -> Union[dict, List[dict]]:
        functions = []
        sequences = []
        
        for k, subworkflow in enumerate(state.funcs):
            root_name = subworkflow["root"]
            
            states = {
                n: State.deserialize(n, s) 
                for n, s in subworkflow["states"].items()
            }
            
            functions.extend(self.encode_state(s) for s in states.values())
            self.states.update(states)
            
            subseq = self.build_sequences(self.states[root_name], self.states)
            branche = []
            
            for i, seq in enumerate(subseq):
                actions = []
                pref = 1
                for item in seq: 
                    actions.append(item.name)
                    pref = pref*item.pref
            
                seq = {
                    f"P{self.idseq+1}" : {
                        "annotations": {"pref" : pref*subworkflow["inf"]},
                        "web" : True,
                        "actions" : ",".join(actions)
                        }
                    }
                
                self.sequences.update(seq)
                branche.append([f"P{self.idseq+1}"])
                self.idseq += 1
           
            sequences.append(branche)
            
        funcs = self.postparallel(sequences, state)
        
        for item in funcs : 
            functions.append(item)
        
        return functions
                    

    def encode_alternative(self, state: Alternative) -> Union[dict, List[dict]]:
        functions = []
        roots = []
        
        for i, subworkflow in enumerate(state.funcs):
            root_name = subworkflow["root"]
            
            states = {
                n: State.deserialize(n, s) 
                for n, s in subworkflow["states"].items()
            }
            
            states[root_name].pref = subworkflow["pref"]
            self.states.update(states)
            
            functions.extend(self.encode_state(s) for s in states.values())
            roots.append(self.states[root_name])
            
            current = self.states[root_name]
            while current.next:
                current = self.states[current.next]
            
            current.next = state.next
            
        state.funcs = roots
            
        return functions


    def encode_switch(self, state: Switch) -> Union[dict, List[dict]]:
        pass


    def _encode_case(self, case: Switch.Case) -> dict:
        pass


    def encode_map(self, state: Map) -> Union[dict, List[dict]]:
        pass


    def encode_loop(self, state: Loop) -> Union[dict, List[dict]]:
        pass


if __name__ == "__main__":
    
    path = sys.argv[1]
    path = Path(path).expanduser().resolve()
    
    if not path.exists():
        print(f"Error: {path} does not exist.")
        sys.exit(1)

    gen = OWKGenerator()
    gen.parse(str(path))
    definition = gen.generate()

    with open("manifest.yaml", 'w') as file:
        yaml.dump(json.loads(definition), file, default_flow_style=False)
    
    import subprocess

    # Run a simple shell command (e.g., 'ls' or 'dir')
    result = subprocess.run(["wskdeploy"], capture_output=True, text=True)

    if result.stdout:
        print( "✅ " + result.stdout )
    else:
        print("STDERR:\n", result.stderr)
        
     