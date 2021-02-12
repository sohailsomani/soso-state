These examples are designed to give both simple and moderately complex examples
of how to use `soso.state` in a Real App (TM).

 * [todo.py](todo.py): Standard TODO example
 * [undo.py](undo.py): Same as above, but with undo behavior
 * [chart.ipynb](notebooks/chart.ipynb): An example of a moderately complex application
   with a jupyter notebook
   
The easiest way to play around with the examples is to use a virtualenv:

```console
git clone https://github.com/sohailsomani/soso-state
cd soso-state
tox --devenv venv -e py38
source venv/bin/activate
python -m pip install -rexamples/requirements-examples.txt
python -m examples.todo
jupyter nbextension enable --py widgetsnbextension
jupyter notebook --notebook-dir=examples/notebooks
```
