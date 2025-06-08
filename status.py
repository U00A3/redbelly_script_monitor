import argparse
from datetime import datetime, timezone, timedelta
import requests
import time
from dateutil import parser
from decimal import Decimal
import re

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

def parse_prometheus_metrics(metrics_text: str) -> dict:
    """Parses Prometheus metrics and returns a dictionary with values"""
    metrics = {}
    lines = metrics_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if line.startswith('#') or not line:
            continue
        
        # Parsing simple metrics without labels
        if '{' not in line:
            parts = line.split(' ', 1)
            if len(parts) == 2:
                name, value = parts
                try:
                    metrics[name] = float(value)
                except ValueError:
                    metrics[name] = value
        else:
            # Parsing metrics with labels
            match = re.match(r'([^{]+)\{([^}]*)\}\s+(.+)', line)
            if match:
                name, labels, value = match.groups()
                try:
                    value = float(value)
                except ValueError:
                    pass
                
                if name not in metrics:
                    metrics[name] = {}
                metrics[name][labels] = value
    
    return metrics

def get_metrics(address: str) -> dict:
    """Fetches and parses Prometheus metrics"""
    try:
        url = address + "/metrics"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return parse_prometheus_metrics(response.text)
    except Exception as e:
        return {}

def format_bytes(bytes_value: float) -> str:
    """Formats bytes to readable form"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} TB"

def format_duration(seconds: float) -> str:
    """Formats seconds to readable form"""
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        return f"{seconds/60:.2f}m"
    elif seconds < 86400:
        return f"{seconds/3600:.2f}h"
    else:
        return f"{seconds/86400:.2f}d"

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
    
    # Get basic status information
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        parts.append(f"❌ Error fetching status: {e}")
        return "\n".join(parts)
    
    # Get Prometheus metrics
    metrics = get_metrics(address)
    
    # Basic information
    parts.append(f"\n📊 Sync Status:")
    parts.append(f"✅ Node has completed initial sync" if data["isRecoveryComplete"] else "⏳ Node is still running initial sync")
    
    # Block information
    parts.append(f"\n🧱 Block Information:")
    parts.append(f"Current block: {data['currentBlock']}")
    parts.append(f"Last block from governors: {data['lastBlockFromGovernors']}")
    parts.append(f"Last sync with governors: {data['lastSyncedWithGovernorNodes']}")
    
    if 'blocks_downloaded' in metrics:
        parts.append(f"Blocks downloaded: {int(metrics['blocks_downloaded'])}")
    if 'pending_blocks_downloaded' in metrics:
        parts.append(f"Pending blocks: {int(metrics['pending_blocks_downloaded'])}")
    
    # Superblock information
    parts.append(f"\n🏛️ Superblock Information:")
    parts.append(f"Current superblock: {data['currentSuperblock']}")
    parts.append(f"Last superblock from bootnodes: {data['lastSuperblockFromBootnodes']}")
    parts.append(f"Last sync with bootnodes: {data['lastSyncedWithBootnodes']}")
    
    # Network Information
    parts.append(f"\n🌐 Network Information:")
    if 'governor_count' in metrics:
        parts.append(f"Governor count: {int(metrics['governor_count'])}")
    if 'is_governor' in metrics:
        is_gov = "✅ YES" if metrics['is_governor'] == 1 else "❌ NO"
        parts.append(f"Is governor: {is_gov}")
    if 'extenders_count' in metrics:
        parts.append(f"Permission extenders: {int(metrics['extenders_count'])}")
    
    # Transaction Information
    parts.append(f"\n💰 Transaction Information:")
    if 'executed_txs_successful' in metrics and isinstance(metrics['executed_txs_successful'], dict):
        successful = sum(v for v in metrics['executed_txs_successful'].values())
        parts.append(f"Successful transactions: {int(successful)}")
    if 'executed_txs_failure' in metrics and isinstance(metrics['executed_txs_failure'], dict):
        failed = sum(v for v in metrics['executed_txs_failure'].values())
        parts.append(f"Failed transactions: {int(failed)}")
    if 'txs_gas_total' in metrics and isinstance(metrics['txs_gas_total'], dict):
        total_gas = sum(v for v in metrics['txs_gas_total'].values())
        parts.append(f"Total gas used: {int(total_gas):,}")
    if 'pending_gas' in metrics:
        parts.append(f"Pending gas: {int(metrics['pending_gas'])}")
    
    # Performance Metrics
    parts.append(f"\n⚡ Performance Metrics:")
    if 'process_cpu_seconds_total' in metrics:
        cpu_time = metrics['process_cpu_seconds_total']
        parts.append(f"Total CPU time: {format_duration(cpu_time)}")
    
    if 'process_resident_memory_bytes' in metrics:
        memory = metrics['process_resident_memory_bytes']
        parts.append(f"Memory usage: {format_bytes(memory)}")
    
    if 'go_goroutines' in metrics:
        parts.append(f"Active goroutines: {int(metrics['go_goroutines'])}")
    
    if 'process_open_fds' in metrics and 'process_max_fds' in metrics:
        open_fds = int(metrics['process_open_fds'])
        max_fds = int(metrics['process_max_fds'])
        fd_usage = (open_fds / max_fds) * 100
        parts.append(f"File descriptors: {open_fds}/{max_fds} ({fd_usage:.1f}%)")
    
    # Block Processing Performance
    if 'block_process_time_sum' in metrics and 'block_process_time_count' in metrics:
        if metrics['block_process_time_count'] > 0:
            avg_process_time = metrics['block_process_time_sum'] / metrics['block_process_time_count']
            parts.append(f"Avg block process time: {avg_process_time*1000:.2f}ms")
    
    # Pricing Information
    parts.append(f"\n💎 Price Information:")
    if 'current_price' in metrics:
        parts.append(f"RBNT/USD price: ${metrics['current_price']:.6f}")
    if 'current_gas_fees' in metrics:
        parts.append(f"Gas fees (USD per 21k units): ${metrics['current_gas_fees']:.4f}")
    
    # Certificate information
    parts.append(f"\n🔐 Certificate Information:")
    parts.append(f"DNS names: {', '.join(data['certificateDnsNames'])}")
    parts.append(f"Valid until: {data['certificatesValidUpto']}")
    
    # Signing address information
    parts.append(f"\n🔑 Signing Address Information:")
    parts.append(f"Address: {data['signingAddress']}")
    balance = Decimal(data['signingAddressBalance']) / ether_in_wei
    parts.append(f"Balance: {balance} RBNT")
    if min_addresss_bal > balance:
        parts.append(f"\033[31m⚠️  WARNING\033[0m: balance is below minimum of {min_addresss_bal} RBNT")
    
    # Permission Tracking
    if 'permission_tracker_cache_hits' in metrics or 'permission_tracker_cache_misses' in metrics:
        parts.append(f"\n🔒 Permission Cache:")
        if 'permission_tracker_cache_hits' in metrics:
            parts.append(f"Cache hits: {int(metrics['permission_tracker_cache_hits'])}")
        if 'permission_tracker_cache_misses' in metrics:
            parts.append(f"Cache misses: {int(metrics['permission_tracker_cache_misses'])}")
        
        if 'permission_tracker_cache_hits' in metrics and 'permission_tracker_cache_misses' in metrics:
            hits = metrics['permission_tracker_cache_hits']
            misses = metrics['permission_tracker_cache_misses']
            total = hits + misses
            if total > 0:
                hit_rate = (hits / total) * 100
                parts.append(f"Cache hit rate: {hit_rate:.1f}%")
    
    # Recovery Information
    if 'time_in_recovery' in metrics and metrics['time_in_recovery'] > 0:
        parts.append(f"\n🔄 Recovery Information:")
        parts.append(f"Time in recovery: {format_duration(metrics['time_in_recovery'])}")
        if 'recovery_blocks_downloaded' in metrics:
            parts.append(f"Recovery blocks downloaded: {int(metrics['recovery_blocks_downloaded'])}")
    
    # Version
    parts.append(f"\n🏷️  Version: {data['version']}")
    
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
