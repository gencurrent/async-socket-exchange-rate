
A simple web server streaming up-to-date exchange rates to the subscribed clients via websocket streaming

# Usage

Subscribe to the server by sending a websocket connection message


## Launching

### General setting   

1. Rename `compose/envs/sample.common.env` into `compose/envs/common.env`
2. Set the missing .env variables with values required for the project to run, e.g., `EMCONT_EXCHANGE_RATES_URL`

### Using Docker

Pull the images   
`docker compose pull`

Build the images   
`docker compose build`

Run the docker compose configuration   
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

Description:   
    Subscribe to the incoming Exchange Rates records live data by:    
    1. Retreiving Exchange Rates for the last 30 minutes;   
    2. Receiving Exchange Rate data live.   
Endpoint: `"/"`   
Message: `"{"action": "subscribe", "message": {"assetId": 1}}"`   
Response:   
1. The initial response is exchange rate records per second for last 30 minutes or 1800 seconds.   
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
2. The incoming live Exchange Rate records:   
Response per each row:   
```JSON
{

    "action": "point",
    "message": {
        "assetName": "EURUSD",
        "time": 1455883484,
        "assetId": 1,
        "value": 1.110481
    }
}
```


# Technical details

## Stack

* Python
  * Poetry
  * FastAPI
  * Beanie
    * Motor
  * pytest / pytest-asyncio
* MongoDB
* Docker / Docker-compose


## General components   

The app components are technically described by the `docker-compose.yaml` file.

### Back end   

The main FastAPI web server to handle incomming connections.   
The only websocket URI it serves is `ws://0.0.0.0:8080/` - the websocket connection function described in [Websocket actions](#websocket-actions).   


### Async periodic tasks    

The asynchronous tasks running in a single thread to:   
1) fetch the exchange rates data from an externcal resource;   
2) save the results into the databasse.   
The primary goal of the asynchonorous tasks is to provide fresh exchange rate records per each second.   

### Data Base   

A MongoDB DBMS instance to store and serve the application data in form of documents.   

## Contribute

Install pre-commit   
`poetry add pre-commit`

Init pre-commit by installing the hooks   
`poetry run pre-commit install`


Test with Mypy against the code (`src/`) depending on the automatically imported `mypy.ini` file:   
`poetry run mypy src`