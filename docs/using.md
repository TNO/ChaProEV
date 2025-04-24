# Installation
```
pip install ChaProEV
```

# Running

The standard way of running the model is to run a case with a code such as
the following:

```python
from ChaProEV import ChaProEV

if __name__ == '__main__':
    case_name: str = 'my_case'
    ChaProEV.run_ChaProEV(case_name)
```

where you need to give a name to your case ('my_case') in the example above.

To run your case, you need to provide general parameters,
scenario parameters, variant parameters, and (optional) inputs.
 
 ## General parameters
The file containing the general parameters (common for all acenarios) is
in your root working folder as is called 
[ChaProEV.toml](general_parameters.md) (click on link for details).
 ## Scenarios

 ## Variants

 ## Inputs