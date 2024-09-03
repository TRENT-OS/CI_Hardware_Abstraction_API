# CI Hardware Abstraction API

_This repository is part of the TRENTOS CI setup._

The TRENTOS CI executes GitHub Action Workflows on hardware development boards.
For this, the TRENTOS test framework communicates with this API, which provides:

- A generalized access to hardware
- Syslog access
- Power Cycling
- Data UART access
- OS Image deployment

To enable this functionality, the following is required from the CI Setup:

- Dev Boards UARTs need to be connected to the deploying server via USB
- Dev Boards need to be powered via PoE by an external switch offering an API to the server
- Dev Boards need to support booting via TFTP