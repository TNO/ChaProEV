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

To run your case, you need to provide
[scenario parameters](scenario.md), [(optional) variant parameters](variants.md),  [(optional) inputs](input.md), and [general parameters](general_parameters.md) (that should not change much from case to case).
