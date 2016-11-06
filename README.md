# API Routes:

| Method | Route              | Description                                                                                                                                                             | Return                                    |
|--------|--------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------|
| POST   | /login             | Post a JSON with a username and password set. Example: {'username': 'test', 'password': 'test'}                                                                         | User Context JSON                         |
| GET    | /chores            | Get a JSON of all available chores                                                                                                                                      | JSON of all chore objects                 |
| GET    | /chores/[USERNAME] | Get a JSON of all chores assigned to [USERNAME]                                                                                                                         | JSON of all chores assigned to [USERNAME] |
| POST   | /update/account/   | Post a JSON with a username and new account value set.  Example: {'username':'test', 'value':1337.50}                                                                   | Update succeed or failed message          |
| POST   | /update/stage      | Post a JSON with a username and new stage value set.  Example: {'username':'test', 'stage':1}                                                                           | Update succeed or failed message          |
| POST   | /assign/chore      | Post a JSON with a username and chore title to set. Example: {'username':'test', 'title':'Mow Lawn'}                                                                    | Assign succeed or failed message          |
| POST   | /create/chore      | Post a JSON with chore parameters to create a new chore {"title": "Chore Title", "description": "Chore Description", "salary": 10.00, "image_path": "Chore Image Path"} | Create succeed or failed message          |
