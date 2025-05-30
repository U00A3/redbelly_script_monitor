# Redbelly Node Status Monitor

A Python script for monitoring the status of a Redbelly node. This tool provides real-time information about your node's synchronization status, block processing, superblocks, certificates, and more.

## Features

- Real-time monitoring of node status
- Block and superblock synchronization status
- Certificate validity monitoring
- Signing address balance tracking
- Configurable refresh rate
- Warning system for critical issues

## Prerequisites

- Python 3.x
- Required Python packages:
  - requests
  - dateutil
  - decimal

## Installation

1. Clone the repository:
```bash
git clone https://github.com/U00A3/redbelly_script_monitor.git
cd redbelly-node-monitor
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

Basic usage:
```bash
python3 status.py
```

### Command Line Options

- `-a, --address`: Address of the Redbelly node's status server (default: http://localhost:6539)
- `-mb, --minBalance`: Minimum signing address balance in RBNT before warning (default: 10)
- `-r, --refreshSeconds`: Frequency to refresh values in seconds (default: 5)

Example with custom parameters:
```bash
python3 status.py -a http://localhost:6539 -mb 20 -r 10
```

## Node Configuration

Make sure your Redbelly node is running with the following flags:
```
--statusserver.addr=127.0.0.1
--statusserver.port=6539
--prometheus.addr=127.0.0.1
```

## Output Information

The script displays:
- Sync Status
- Block Information
- Superblock Information
- Certificate Information
- Signing Address Information
- Node Version

## Warning System

The script will show warnings (in red) for:
- Low signing address balance
- Block synchronization issues
- Superblock synchronization issues
- Certificate expiration

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details. 