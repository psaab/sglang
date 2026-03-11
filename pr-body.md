## Motivation

SGLang currently assumes IPv4 in many places — `socket.gethostbyname()` calls (IPv4-only), naive `host.split(":")` parsing that breaks on IPv6 colons, hard-coded `127.0.0.1` loopback, and bare IPv6 addresses in URLs without bracket wrapping. This makes SGLang unusable on IPv6-only or dual-stack networks.

This PR adds comprehensive IPv6 support so that SGLang works correctly on both IPv4 and IPv6 networks without any special configuration.

## Modifications

The changes are organized into 7 logical groups:

### 1. Core IPv6 utilities (`srt/utils/common.py`)
- Add `resolve_hostname()` — uses `socket.getaddrinfo()` instead of `gethostbyname()` to support both IPv4 and IPv6
- Add `parse_host_port()` — safely parses `host:port` strings, handling bracketed IPv6 (`[::1]:8000`) and plain IPv4 (`127.0.0.1:8000`)
- Update `is_port_available()`, `get_free_port()`, `bind_port()`, `get_open_port()` to try IPv6 first with IPv4 fallback
- Add `zmq.IPV6` flag in `get_zmq_socket_on_host()` when the host is IPv6
- Exclude `::1` from local IP detection in `get_local_ip_by_remote()` and `get_local_ip_by_nic()`

### 2. Replace `gethostbyname` with IPv6-compatible alternatives
- `dumper.py` — uses inline `socket.getaddrinfo()` (avoids sglang imports)
- `loader.py`, `model_runner.py` — use `resolve_hostname()`
- `conn.py` (disaggregation) — simplified with `parse_host_port()` + `resolve_hostname()`

### 3. Fix host:port parsing
- `server_args.py` — use `parse_host_port()` instead of `.split(":")`
- `data_parallel_controller.py` — replace multi-branch parsing with `parse_host_port()` + `format_tcp_address()`
- `model_runner.py`, `encode_server.py`, `encode_grpc_server.py`, `remote_instance.py`, `mindspore_runner.py`, `mooncake_store.py` — use `parse_host_port()` / `format_tcp_address()` consistently

### 4. Wrap IPv6 addresses in brackets for URLs and address strings
- Apply `maybe_wrap_ipv6_address()` across 18 files wherever `host:port` strings are constructed for URLs, log messages, or network addresses
- Fix `normalize_base_url()` in `utils.py` to wrap IPv6 hosts in brackets
- Covers: `bench_serving.py`, `compile_deep_gemm.py`, server entrypoints, disaggregation modules, model loader, weight loader utils, etc.

### 5. Default to IPv6 loopback (`::1`) instead of `127.0.0.1`
- Change `ServerArgs.host` default from `"127.0.0.1"` to `"::1"` (works on both dual-stack and IPv6-only systems)
- Update `multimodal_gen/server_args.py`, `gpu_worker.py`, `shm_broadcast.py` similarly

### 6. Set `zmq.IPV6` flag on ZMQ sockets
- Enable IPv6 on all ZMQ PUB, SUB, PUSH, PULL, ROUTER, DEALER sockets that may bind/connect to IPv6 endpoints
- Files: `common.py`, `dumper.py`, `scheduler_client.py`, `kv_events.py`, `encode_server.py`, `expert_backup_client.py`, `expert_backup_manager.py`
- Fix `kv_events.py` `"::" in endpoint` heuristic that falsely matched IPv6 addresses

### 7. Enhanced Mooncake transfer engine logging
- Add detailed logging around transfer failures, session lifecycle, and ZMQ operations in `mooncake/conn.py` and `mooncake_transfer_engine.py` for debugging connectivity issues on IPv6 networks

## Accuracy Tests

This PR does not modify model forward code, kernels, or inference logic. All changes are to networking/address handling code paths. No accuracy impact.

## Benchmarking and Profiling

This PR does not affect inference speed. Changes are limited to:
- Server startup address binding (one-time cost)
- Log message formatting (negligible)
- Socket creation order (IPv6 first, IPv4 fallback — same total cost)

## Checklist

- [x] Format code according to the project style guide
- [ ] Add unit tests for `parse_host_port()` and `resolve_hostname()` utilities
- [ ] Update documentation for IPv6 default (`::1`) and configuration
- [x] No accuracy or speed impact (networking-only changes)
- [x] Follow the SGLang code style guidance
