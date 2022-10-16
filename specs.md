Users Database

field        | type         | desc
-------------|--------------|----------------------------------------
uuid         | str          | the user id
pwd          | str          | the user "password". Unchangeable.
name         | str          | user settable name. 8 char max.
lastaccess   | number       | last timestamp this user was accessed



Pays Hoff Circle Database

field        | type         | desc
-------------|--------------|----------------------------------------
gameid       | str          | identifying uuid for the game
userlist     | str          | comma separated list of users, in order
nextuser     | str          | uuid of the user who is next
noaddyet     | str          | CSL of users who havent added yet
choices      | str          | TSL of string choices
lockedin     | bool         | is the |choices| locked? game over.
lastaccess   | number       | last timestamp this game was accessed



Democracy Database

field        | type         | desc
-------------|--------------|----------------------------------------
