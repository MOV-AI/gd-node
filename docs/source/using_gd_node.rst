Using GD Node
=============

Callback builtins
-----------------

The GD Node callbacks have access to the following builtins:

* ``scopes``: A ScopesTree **instance**
* ``Package``: Package class
* ``Message``: Message class
* ``Ports``: Ports class
* ``StateMachine``: StateMachine class
* ``Var``: UserVar class - used to set, get and delete node scoped variables
* ``Robot``: Robot class **instance**
* ``FleetRobot``: FleetRobot class
* ``logger``: LogAdapter **instance** - logger that should be used in callbacks
* ``PortName``: Name of the port that triggered the callback
* ``SM``:UserSM class
* ``Callback``: Callback class
* ``Lock``: UserLock class - used to interact with locks
* ``print``: Debug log function
* ``Scene``: Active scene **instance**, None if active_scene is not specified
* ``NodeInst``: NodeInst class
* ``Container``: Container class
* ``Configuration``: Configuration class

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
