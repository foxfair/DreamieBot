# DreamieBot
Hunting for your dreamie in ACNH.


# What command this bot provides:

For users they can use these commands:
   * 'request': to request a new villager. The bot should generate a request ID and send back to user.
   'status': to check the status of their requests. Status enum(Enumerated type) are:
    ['PENDING', 'PROCEED', 'FOUND', 'CLOSED', 'READY', 'CANCEL']
        * PENDING: The default status of every new request, which is unreviewed and not approved yet.
        * PROCEED: When a staff has reviewed and approved a request, the status is changed to proceed.
        * FOUND: A staff has found a requested villager.
        * CLOSED: The request has been fulfilled and closed.
        * READY: A user indicates that there is an open plot, will be ready to welcome a dreamie home.
        * CANCEL: A request is cancelled before completion. It is either cancelled by a user or a staff.
   * 'ready': to indicate the user is ready now or in the next three days.
   * 'cancel': to cancel a request. optional arguments: a request ID, or a villager name.

For staff, we can do these tasks:
   * 'list': List all requests.
   * 'review': Review a request to approve or deny, so that move it to the next state (ready to proceed & recruit a villager for them). Optional arguments: a request ID.
   * 'found': A staff has found a villager, and moved into fostering house. optional arguments: a request ID (Consider to place villager's name here too. But if a villager is popular and multiple requests want it, how to assign a villager?)
   * 'close': Close a request. optional arguments: a request ID, or a user name.
   * 'inspect': Inspect user information to setup for staff.

