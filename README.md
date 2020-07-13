# DreamieBot
Hunting for your dreamie in ACNH.


# What command this bot provides:

For users they can use these commands:
   * 'apply': Apply to request a new villager. The bot should generate an application ID and send back to user.
   * 'status': to check the status of their requests. Status enum(Enumerated type) are:
    ['PENDING', 'PROCESSING', 'FOUND', 'CLOSED', 'READY', 'CANCEL']
        * PENDING: The default status of every new request, which is unreviewed and not approved yet.
        * PROCESSING: When a staff has reviewed and approved a request, the status is changed to processing.
        * FOUND: A staff has found a requested villager and fostered to wait for an open plot.
        * CLOSED: The application has been fulfilled and closed.
        * READY: A user indicates that there is an open plot, will be ready to welcome a dreamie home.
        * CANCEL: An application is cancelled before completion. It is either cancelled by a user or reviewed then denied by a staff.
   * 'ready': to indicate the user is ready now or in the next three days.
   * 'cancel': to cancel a request. required argument: an application ID.

For staff, we can do these tasks:
   * 'list': List all requests or a specified request. Including cancelled and closed requests.
   * 'review': Review a request to approve or deny, so that move it to the next state (ready to proceed & recruit a villager for them)
        required argument: an application ID.
   * 'found': A staff has found a villager, and moved into fostering house. required argument: an application ID.
   * 'close': Close a request. required argument: an application ID.
   * 'lock': Lock/unlock the bot and deny or accept future applications until its status is changed.
