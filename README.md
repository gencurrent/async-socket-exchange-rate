
A simple web server streaming up-to-date exchange rates to the subscribed clients via websocket streaming

# Usage

Subscribe to the server by sending a websocket connection message   


## Launching   

### Using Docker   

`docker compose pull`   
`docker compose build`   
`docker compose up`   

### Asynchronous tasks

Run asynchornous tasks manually:
`docker compose exec backend bash`   
`poetry run python async_tasks/async_periodic_tasks.py`   

### Mongo   
Connect to the Mongo DB instance:   
`docker compose exec db sh`    
`mongosh $MONGO_CONNECTION_URI`   
`show dbs`  to list all the databases
`use db`  to switch to the backend database


## Websocket actions

The only application endpoint is   
Endpoint: `"/"`   

### 1. Retreive the available assets

message: `"{"action": "assets", "message": {}}"`   
Response sample:   
```JSON
{
    "action": "assets",
    "message": {
        "assets": [
            {
                "id": 1,
                "name": "EURUSD"
            },
            {
                "id": 2,
                "name": "USDJPY"
            }
        ]
    }
}
```

### 2. Subscribe to the specified asset

Endpoint: `"/"`   
Message: `"{"action": "subscribe", "message": {"assetId": 1}}"`   
Response sample:   
```JSON
{
    "message": {
        "points": [
            {
                "assetName": "EURUSD",
                "time": 1455883484,
                "assetId": 1,
                "value": 1.110481
            },
            {
                "assetName": "EURUSD",
                "time": 1455883485,
                "assetId": 1,
                "value": 1.110948
            }
        ]
    },
    "action": "asset_history"
}
```


# Technical details   

## Stack   

* Python
  * Poetry
  * FastAPI
  * Motor
* MongoDB
* Docker / Docker-compose
