# SAFE: Secure Aggregation with Failover and Encryption

This respository contains a proof-of-concept implementation
of the [SAFE](https://arxiv.org/abs/2108.05475) algorithm. For comparison, the repository also contains implementations of the original [Practical Secure Aggregation](https://dl.acm.org/doi/10.1145/3133956.3133982) algorithm,
developed by Google, as well as federated aggregation without protection.

A high-level overview
of Federated Learning and Secure Aggregation for the Cable industry can be found in
[SCTE Technical Journal Vol 1 No 3, Page 79](https://wagtail-prod-storage.s3.amazonaws.com/documents/SCTE_Technical_Journal_V1N3.pdf).

## Secure Aggregation
Secure Aggregation is used in Federated Learning as part of the training phase to coordinate
learned parameters with a central coordinator in a mechanism referred to as Federated Averaging
typically performed during some stochastic gradient descent optimization process. 
Secure Aggregation allows parameters contributed by local learners to be kept confidential 
(not shared with a central controller or other learners) while still making progress on
the optimization by computing averages over the confidential values.

The original algorithm scales quadrtically in the number of learners whereas our SAFE
algorithm scales linearly and is more resurce efficient and easier to implement on constrained
devices such as network equipment.

## Getting Started
If you want to run both the controller and the client locally docker is recommended.

To get started first install [Docker](https://docker.com). The [docker-compose tool](https://docs.docker.com/compose/) comes with 
Docker for Mac but must be installed separately for other platforms. On Mac it is invoked with
`docker compose` instead of `docker-compose`.

When docker is running (`docker ps` should not return errors), run the controller with:
```
docker-compose build && docker-compose up
```
from the safe root directory. It will run the controller and SAFE runtime in a couple of docker containers in the foreground. To stop the
system do `Ctrl-C` in the terminal. You can run it in the background by adding `-d` and then stop it with `docker-compose down` as well.

Start first client with:
```
./client.sh
```
In a second terminal start a second client with:
```
./client.sh
```
Finally in a third terminal start a client with:
```
./client.sh
```

Now add values and observe aggregates being computed. Several aggregation
rounds may be submitted. To exit out of the shell simply press enter at
the aggregate prompt. Any number of clients may be added this way.
When a client first starts up it will be assigned an index on the aggregation
chain. When the initiator starts only clients with an assigned index at that point
will be included in the aggregation.

To reset all client registrations and start up a new set of clients run:
```
./client.sh clear
```

To use your own custom config run:
```
SAFE_CONFIG=<path to safe config file> ./client.sh 
```

## Client Configuration Options
The client can be configures with the [config/config.json](config/config.json)
file. 

The following options may be set:

| Option | Description | Default |
| --- | --- | --- |
| `controller` | URL of controller|http://localhost:8088 |
| `weighted`| Should an extra parameter be aggregated for weights | false |
| `features` | Number of features to aggregate | 1 |
| `ag_type` | Aggregation type | SAFE (can also be [BON](https://dl.acm.org/doi/10.1145/3133956.3133982) and `INSEC` -aggregation w/o protection) |
| `should_encrypt`| Should aggregate be encrypted | true |
| `aggregation_timeout` | when to give up on aggregate (seconds) | 10 |
| `should_debug` | debug logs | true | 
| `groups` | number of parallel groups in aggregation | 1 |
| `group` | which group this client belongs to | 1 |
| `key_size` | key size used during encryption | 512 |
| `poll_time` | time to rety long polling (seconds) | 0.01 |
| `precision` | precision in decimals of aggregation | 5 |
| `max_random` | initial seed max value | 1000 |
| `restart_wait` | on initiator failure time to wait to pick new initiator (seconds) | 10 |


## Controller Configuration Options
The aggregation controller is configured with environment variables
set in the [docker-compose.yaml](docker-compose.yaml) file.

The following variables may be set:

| Variable | Description | Default |
| --- | --- | --- |
| `PROGRESS_TIMEOUT` | progress timout (seconds) when client will be skipped | 5 |
| `AGGREGATION_TIMEOUT` | aggregation timout (seconds) when aggregation wil be restarted | 10 |
| `SHOULD_DEBUG` | debug logs | yes |
| `POLL_TIME` | internal long poll max wait for values (seconds) | 10 |
| `YIELD_TIME` | time to wait between checking for values in long poll (seconds) | 0.005 |

## Authentication
By creating a `.env` file containing:
```
AUTH_ENABLED=yes
```
HTTP Basic Authentication may be enabled to restrict access to
different namespaces in a controller.

Namespace credentials can be managed with the 
```
./add_namespace.sh
```
which produces a namespace mapping file with encrypted 
passwords at `config/namespaces.json`.

The namespace may then be passed into APIs with the correct
basic authentication header containing the credentials to gain access.


## API Documentation
Swagger REST API documentation for the controller can be explored when the controller is running on:
[http://localhost:8088/apidocs/](http://localhost:8088/apidocs/).

Client PyDoc API can be expored when the controller is running on:
[http://localhost:9099/aggregation/](http://localhost:9099/aggregation/).

## Tests
Run the tests with
```
docker-compose -f docker-compose-test.yaml build && docker-compose -f docker-compose-test.yaml up
```
The tests to be run are specified in [tests/tests.conf](tests/tests.conf)
with the syntax:
```
AGGREGATION_METHOD EXPECTED_VALUE VALUE_1 VALUE_2 ... VALUE_N
```

## Use Cases

*  Web survey system [SPoKE](https://github.com/cablelabs/spoke). 

