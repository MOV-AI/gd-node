Using GD Node
=============

Callback builtins
-----------------

The GD Node callbacks have access to the following builtins:

* ``Callback``: Callback class
* ``Configuration``: Configuration class
* ``Container``: Container class
* ``FleetRobot``: FleetRobot class
* ``gd``: Node shared object - used to get param and interact with oports
* ``Lock``: UserLock class - used to interact with locks
* ``logger``: LogAdapter **instance** - logger that should be used in callbacks
* ``Message``: Message class
* ``NodeInst``: NodeInst class
* ``Package``: Package class
* ``PortName``: Name of the port that triggered the callback
* ``Ports``: Ports class
* ``print``: Debug log function
* ``Robot``: Robot class **instance**
* ``run``: Function to run another callback (from the callback itself)
* ``Scene``: Active scene **instance**, None if active_scene is not specified
* ``scopes``: A ScopesTree **instance**
* ``SM``:UserSM class
* ``StateMachine``: StateMachine class
* ``Var``: UserVar class - used to set, get and delete node scoped variables

If you are using the enterprise version of MOV.AI the following are also available:

* ``Alerts``: Alerts class
* ``Annotation``: Annotation class
* ``GraphicAsset``: GraphicAsset class
* ``GraphicScene``: GraphicScene class
* ``Layout``: Layout class
* ``metrics``: Metrics class **instance**
* ``Task``: Task class
* ``TaskEntry``: TaskEntry class
* ``TaskTemplate``: TaskTemplate class
