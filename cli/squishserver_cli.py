#!/usr/bin/env python3
"""
Squish Server CLI Management Module

Handles Squish server lifecycle management including:
- Starting squishserver with configurable host/port
- Stopping running squishserver instances
- Checking server status
- Configuration management

IMPORTANT: This file requires Python 3.10+ due to f-string usage and type hints.
Do not use with Python 2.x - it will cause syntax errors.
"""

import subprocess
import os
import time
import signal
import psutil
from typing import Dict, List, Optional, Tuple

# Import shared configuration
from . import (
    SQUISH_SERVER, 
    DEFAULT_HOST, 
    DEFAULT_PORT,
    validate_squish_installation,
    format_server_key
)

# Global tracking for managed server processes
_managed_servers: Dict[str, Dict] = {}

def start_squish_server(host: str = DEFAULT_HOST, port: str = DEFAULT_PORT, 
                       daemon: bool = True, verbose: bool = False, 
                       logfile: str = "", config_file: str = "") -> Dict:
    """
    Start a Squish server with configurable options.
    
    Args:
        host: Host address to bind to (default: localhost)
        port: Port to listen on (default: 4322)
        daemon: Run as daemon process (default: True)
        verbose: Enable verbose output (default: False)
        logfile: Path to log file (optional)
        config_file: Path to custom config file (optional)
    
    Returns:
        Dict with the following structure:
        {
            "status": int,  # 0 for success, 1 for error
            "message": str,
            "server_info": {
                "host": str,
                "port": str,
                "pid": int,
                "daemon": bool,
                "logfile": str,
                "server_key": str  # Unique key for this server instance
            }
        }
    """
    # Validate Squish installation
    is_valid, validation_msg = validate_squish_installation()
    if not is_valid:
        return {
            "status": 1,
            "message": validation_msg,
            "server_info": {}
        }
    
    # Create unique server key
    server_key = format_server_key(host, port)
    
    # Try and start server each time. If its already running command will be ignored anyways.
    
    # Build command
    cmd = [SQUISH_SERVER]
    
    # Add host and port
    cmd.extend(["--host", host])
    cmd.extend(["--port", port])
    
    # Add optional flags
    if daemon:
        cmd.append("--daemon")
    
    if verbose:
        cmd.append("--verbose")
    else:
        cmd.append("--quiet")
    
    if logfile:
        cmd.extend(["--logfile", logfile])
    
    if config_file:
        cmd.extend(["--configfile", config_file])
    
    debug_msg = f"Starting Squish server: {' '.join(cmd)}"
    
    try:
        # Start the server
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it a moment to start
        time.sleep(2)
        
        # Check if process is still running
        if process.poll() is None:
            # Server started successfully
            server_info = {
                "host": host,
                "port": port,
                "pid": process.pid,
                "daemon": daemon,
                "logfile": logfile,
                "server_key": server_key,
                "process": process,
                "start_time": time.time()
            }
            
            # Track the managed server
            _managed_servers[server_key] = server_info
            
            return {
                "status": 0,
                "message": f"Squish server started successfully on {host}:{port} (PID: {process.pid})",
                "server_info": {
                    "host": host,
                    "port": port,
                    "pid": process.pid,
                    "daemon": daemon,
                    "logfile": logfile,
                    "server_key": server_key
                }
            }
        else:
            # Server failed to start
            stdout, stderr = process.communicate()
            return {
                "status": 1,
                "message": f"{debug_msg}\nServer failed to start.\nStdout: {stdout}\nStderr: {stderr}",
                "server_info": {}
            }
    
    except Exception as e:
        return {
            "status": 1,
            "message": f"{debug_msg}\nError starting server: {str(e)}",
            "server_info": {}
        }

def stop_squish_server(host: str = DEFAULT_HOST, port: str = DEFAULT_PORT, 
                      force: bool = False) -> Dict:
    """
    Stop a running Squish server.
    
    Args:
        host: Host address of server to stop (default: localhost)
        port: Port of server to stop (default: 4322)
        force: Force kill the server if graceful stop fails (default: False)
    
    Returns:
        Dict with the following structure:
        {
            "status": int,  # 0 for success, 1 for error
            "message": str,
            "stopped": bool
        }
    """
    # Validate Squish installation
    is_valid, validation_msg = validate_squish_installation()
    if not is_valid:
        return {
            "status": 1,
            "message": validation_msg,
            "stopped": False
        }
    
    server_key = format_server_key(host, port)
    
    # First try the official stop command
    cmd = [SQUISH_SERVER, "--stop", "--host", host, "--port", port]
    debug_msg = f"Stopping Squish server: {' '.join(cmd)}"
    
    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Give it a moment to stop
        time.sleep(2)
        
        # Check if server is still running
        if not is_server_running(host, port):
            # Remove from managed servers
            if server_key in _managed_servers:
                del _managed_servers[server_key]
            
            return {
                "status": 0,
                "message": f"Squish server on {host}:{port} stopped successfully",
                "stopped": True
            }
        
        # If graceful stop didn't work and force is requested
        if force:
            return _force_stop_server(host, port, server_key)
        
        return {
            "status": 1,
            "message": f"{debug_msg}\nServer may still be running. Use force=True to force kill.\nStdout: {process.stdout}\nStderr: {process.stderr}",
            "stopped": False
        }
    
    except subprocess.TimeoutExpired:
        if force:
            return _force_stop_server(host, port, server_key)
        return {
            "status": 1,
            "message": f"Stop command timed out. Server may still be running. Use force=True to force kill.",
            "stopped": False
        }
    except Exception as e:
        return {
            "status": 1,
            "message": f"{debug_msg}\nError stopping server: {str(e)}",
            "stopped": False
        }

def _force_stop_server(host: str, port: str, server_key: str) -> Dict:
    """
    Force stop a server by killing the process.
    """
    try:
        # Try to kill managed process first
        if server_key in _managed_servers:
            server_info = _managed_servers[server_key]
            process = server_info.get("process")
            pid = server_info.get("pid")
            
            if process and process.poll() is None:
                try:
                    process.terminate()
                    time.sleep(2)
                    if process.poll() is None:
                        process.kill()
                    del _managed_servers[server_key]
                    return {
                        "status": 0,
                        "message": f"Force stopped managed Squish server on {host}:{port} (PID: {pid})",
                        "stopped": True
                    }
                except Exception as e:
                    pass
        
        # Find and kill squishserver processes on the specified port
        killed_pids = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'squishserver' in proc.info['name']:
                    cmdline = proc.info['cmdline'] or []
                    # Check if this process is using our port
                    if '--port' in cmdline:
                        port_idx = cmdline.index('--port')
                        if port_idx + 1 < len(cmdline) and cmdline[port_idx + 1] == port:
                            proc.terminate()
                            killed_pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
                continue
        
        if killed_pids:
            # Wait for processes to terminate
            time.sleep(2)
            
            # Force kill if still running
            for pid in killed_pids:
                try:
                    proc = psutil.Process(pid)
                    if proc.is_running():
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Remove from managed servers
            if server_key in _managed_servers:
                del _managed_servers[server_key]
            
            return {
                "status": 0,
                "message": f"Force stopped Squish server on {host}:{port} (killed PIDs: {killed_pids})",
                "stopped": True
            }
        else:
            return {
                "status": 1,
                "message": f"Could not find squishserver process running on port {port}",
                "stopped": False
            }
    
    except Exception as e:
        return {
            "status": 1,
            "message": f"Error force stopping server: {str(e)}",
            "stopped": False
        }

def is_server_running(host: str = DEFAULT_HOST, port: str = DEFAULT_PORT) -> bool:
    """
    Check if a Squish server is running on the specified host and port.
    
    Args:
        host: Host to check (default: localhost)
        port: Port to check (default: 4322)
    
    Returns:
        bool: True if server is running, False otherwise
    """
    try:
        # Try to connect to the port
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        return result == 0
    except Exception:
        return False

