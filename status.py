import argparse
from datetime import datetime, timezone, timedelta
import requests
import time
from dateutil import parser
from decimal import Decimal

ether_in_wei = Decimal("1000000000000000000")
blockChanges: list[tuple[int, datetime]] = []

def clear_screen():
    print("\033[2J\033[H", end='', flush=True)

def get_block_ps(blockChange: list[tuple[int, datetime]]) -> float:
    (startBlock, startTime) = blockChange[0]
    (endBlock, endTime) = blockChange[-1]
    timeChange = endTime.replace(tzinfo=timezone.utc) - startTime.replace(tzinfo=timezone.utc)
    if timeChange.total_seconds() == 0:
        return 0
    return float(endBlock - startBlock) / timeChange.total_seconds()

def run_loop(address: str, min_addresss_bal: int, refresh_seconds: int):
    try:
        while True:
            result = monitor(address, min_addresss_bal)
            clear_screen()
            print(result)
            time.sleep(refresh_seconds)
    except KeyboardInterrupt:
        print("\nExiting")
    except BaseException as e:
        print(f"\nGot error when connecting to {address}, be sure status server is enabled in SEVM with flags --statusserver.addr=127.0.0.1 --statusserver.port=6539")
        print(e)
        exit(1)

def monitor(address: str, min_addresss_bal: int) -> str:
    url = address + "/status"
    parts = []
    parts.append(f"Monitoring url {url}")
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    data = response.json()
    
    # Basic information
    parts.append(f"\nSync Status:")
    parts.append(f"Node has completed initial sync" if data["isRecoveryComplete"] else "Node is still running initial sync")
    
    # Block information
    parts.append(f"\nBlock Information:")
    parts.append(f"Current block: {data['currentBlock']}")
    parts.append(f"Last block from governors: {data['lastBlockFromGovernors']}")
    parts.append(f"Last sync with governors: {data['lastSyncedWithGovernorNodes']}")
    
    # Superblock information
    parts.append(f"\nSuperblock Information:")
    parts.append(f"Current superblock: {data['currentSuperblock']}")
    parts.append(f"Last superblock from bootnodes: {data['lastSuperblockFromBootnodes']}")
    parts.append(f"Last sync with bootnodes: {data['lastSyncedWithBootnodes']}")
    
    # Certificate information
    parts.append(f"\nCertificate Information:")
    parts.append(f"DNS names: {', '.join(data['certificateDnsNames'])}")
    parts.append(f"Valid until: {data['certificatesValidUpto']}")
    
    # Signing address information
    parts.append(f"\nSigning Address Information:")
    parts.append(f"Address: {data['signingAddress']}")
    balance = Decimal(data['signingAddressBalance']) / ether_in_wei
    parts.append(f"Balance: {balance} RBNT")
    if min_addresss_bal > balance:
        parts.append(f"\033[31mWARNING\033[0m: balance is below minimum of {min_addresss_bal} RBNT")
    
    # Version
    parts.append(f"\nVersion: {data['version']}")
    
    return "\n".join(parts)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch the stats of a local Redbelly node")
    parser.add_argument("-a", "--address", type=str, default="http://localhost:6539", help="Address of the Redbelly node's status server")
    parser.add_argument("-mb", "--minBalance", type=int, default=10, help="Minimum signing address balance in RBNT before warning")
    parser.add_argument("-r", "--refreshSeconds", type=int, default=5, help="Frequency to refresh values")
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_args()
    run_loop(args.address, args.minBalance, args.refreshSeconds)
