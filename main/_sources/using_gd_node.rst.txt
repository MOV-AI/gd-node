Using GD Node
=============

Callback builtins
-----------------

The GD Node callbacks have access to the following builtins:

* ``Callback``: Callback class
* ``Configuration``: Configuration class - used to get Configuration files
* ``Container``: Container class
* ``FleetRobot``: FleetRobot class
* ``gd``: Node shared object - used to get param and interact with oports

   .. code-block:: python

      # Get the value of a param
      param_value = gd.params('param_name')

      # Set the value of an oport
      gd.oport('port_name').send(msg)

* ``Lock``: UserLock class - used to interact with locks

   .. code-block:: python

      # Acquire a lock
      Lock(Robot.RobotName, persistent=True).acquire()

* ``logger``: LogAdapter **instance** - logger that should be used in callbacks
* ``Message``: Message class
* ``NodeInst``: NodeInst class
* ``Package``: Package class
* ``PortName``: Name of the port that triggered the callback

   .. code-block:: python

      # Log the name of the port that triggered the callback
      logger.info("The callback was triggered by port: %s", PortName)

* ``Ports``: Ports class
* ``print``: Debug log function
* ``Robot``: Robot class **instance**
* ``run``: Function to run another callback (from the callback itself)
* ``Scene``: Active scene **instance**, None if active_scene is not specified
* ``scopes``: A ScopesTree **instance**
* ``SM``: UserSM class
* ``StateMachine``: StateMachine class
* ``Var``: UserVar class - used to set, get and delete node scoped variables

If you are using the enterprise version of MOV.AI the following are also available:

* ``Alerts``: Alerts class
* ``Annotation``: Annotation class
* ``GraphicAsset``: GraphicAsset class
* ``GraphicScene``: GraphicScene class
* ``Layout``: Layout class
* ``metrics``: Metrics class **instance** - used to send metrics
* ``Task``: Task class
* ``TaskEntry``: TaskEntry class
* ``TaskTemplate``: TaskTemplate class
