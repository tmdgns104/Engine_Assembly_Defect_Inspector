"""Foreground systemd entrypoint for the complete local inspection runtime."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent


def plc_contract(config):
    contract = config.get('plc_contract', 'STANDALONE_V3')
    if contract not in ('STANDALONE_V3', 'LEGACY_THREE_BOOL', 'OPENER_CYCLIC'):
        raise ValueError('UNSUPPORTED_EXPLICIT_PLC_CONTRACT')
    if contract == 'OPENER_CYCLIC' and config.get('legacy_publication_enabled', False):
        raise ValueError('MULTIPLE_PLC_PUBLISHERS_FORBIDDEN')
    return contract


def check_port_available(host, port):
    import socket
    with socket.socket() as probe:
        # Uvicorn uses SO_REUSEADDR as well. A closed predecessor connection
        # in TIME_WAIT is not an active competing listener.
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind((host, port))


def settings(path):
    value = json.loads(path.read_text(encoding='utf-8'))
    for key in ('package', 'station', 'data_root', 'pythonpath', 'line_profile'):
        target = (path.parent/value[key]).resolve()
        if not target.is_relative_to(ROOT.parent):
            raise ValueError('DEVICE_LOCAL_PATH_REQUIRED:'+key)
        value[key] = target
    if value.get('plc_ip') != '192.168.50.3' or value.get('plc_local_ip') != '192.168.50.2':
        raise ValueError('CONFIRMED_FIELD_PLC_ADDRESSES_REQUIRED')
    if value.get('listen_host') not in ('192.168.50.2', '0.0.0.0', '127.0.0.1'):
        raise ValueError('UNREVIEWED_BIND_ADDRESS')
    return value


def line_profile(path):
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('mode') not in ('NO_PUSHER_AUTO_INSPECTION', 'EXISTING_PLC_INSPECTION') or value.get('pusher_enabled') is not False:
        raise ValueError('JETSON_PUSHER_COMMANDS_DISABLED_REQUIRED')
    if type(value.get('field_profile_verified')) is not bool:
        raise ValueError('EXPLICIT_FIELD_VERIFICATION_REQUIRED')
    for key in ('arrival_deadline_s', 'assembly_deadline_s'):
        if type(value.get(key)) not in (int, float) or not 1 <= value[key] <= 120:
            raise ValueError('BOUNDED_SOFTWARE_DEADLINE_REQUIRED:'+key)
    if type(value.get('min_free_bytes')) is not int or value['min_free_bytes'] < 1_000_000_000:
        raise ValueError('MINIMUM_LOCAL_STORAGE_RESERVE_REQUIRED')
    return value


def close_resources(runtime, assembly, gateway, adapter, lock):
    """Even a failed constructor or failed runtime close must release the child."""
    try:
        if runtime is not None:
            runtime.close()
        else:
            try:
                if assembly is not None: assembly.close()
            finally:
                if gateway is not None: gateway.close()
    finally:
        try:
            if adapter is not None: adapter.close()
        finally:
            lock.close()


def close_adapter_on_shutdown(app, adapter):
    """Release owned IPC before Uvicorn restores and re-raises SIGTERM.

    The outer finally remains a fallback for startup failures. On normal
    systemd shutdown it may never run, so the adapter must join its child
    within ASGI lifespan, after the runtime stops publishing results.
    """
    if adapter is None:
        return
    import asyncio
    from contextlib import asynccontextmanager
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application):
        try:
            async with original_lifespan(application) as state:
                yield state
        finally:
            await asyncio.to_thread(adapter.close)

    app.router.lifespan_context = lifespan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    config = settings(args.config.resolve())
    profile = line_profile(config['line_profile'])
    from src.configuration import profile_settings, station_settings, snapshot, validate_package_settings
    profile = profile_settings(profile)
    contract = plc_contract(config)
    expected_mode = 'EXISTING_PLC_INSPECTION' if contract in ('LEGACY_THREE_BOOL', 'OPENER_CYCLIC') else 'NO_PUSHER_AUTO_INSPECTION'
    if profile['mode'] != expected_mode:
        raise ValueError('PLC_CONTRACT_AND_PROFILE_MODE_MISMATCH')
    sys.path.insert(0, str(config['pythonpath']))
    # Child camera/inference processes inherit the same verified overlay.
    os.environ['PYTHONPATH'] = os.pathsep.join([str(ROOT), str(config['pythonpath'])])
    from launch_live import check_files
    from src.vision.misassembly_shadow import verify_assets
    from src.vision.integrated_decision import POLICY
    station, identity = check_files(config['package'], config['station'], plc_bench=True)
    from src.recipe.package import load_package
    validate_package_settings(load_package(config['package']))
    station = station_settings(station)
    identity['configuration'] = snapshot()
    assets = ROOT.parent/'assets/misassembly_runtime'
    manifest = verify_assets(assets)
    identity.update(plc_contract=contract, mode=profile['mode'],
        final_policy=POLICY, profile_path=str(config['line_profile']),
        inference_dependencies=len(manifest['files']), laptop_required=False)
    if contract == 'OPENER_CYCLIC':
        identity.update(backend='OPENER_CYCLIC',
            network_plc_writes_enabled=config.get('cyclic_publication_enabled') is True,
            transport_activation_approved=config.get('cyclic_transport_activation_approved') is True,
            explicit_result_writer_enabled=False, synthetic_result_generator_enabled=False)
    if args.check_only:
        print(json.dumps(identity, ensure_ascii=False))
        return
    # One supervisor. The installer removes only the backed-up project cron.
    import fcntl
    config['data_root'].mkdir(parents=True, exist_ok=True)
    lock = (config['data_root']/'standalone-owner.lock').open('a+b')
    adapter = gateway = assembly = runtime = None
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        check_port_available(config['listen_host'], config['port'])
        from src.control.standalone_plc import LineGateway
        from src.control.omron_cip import LegacyStandaloneGateway
        from src.vision.assembly_process import ProcessAssemblyInspector
        from src.runtime.bootstrap import build_runtime
        from apps.edge_service.integration_api import create_integrated_app
        from src.runtime.standalone_web import configure_line_web
        import uvicorn
        if contract == 'OPENER_CYCLIC':
            from src.runtime.opener_process import OpenerProcess
            binary = (ROOT/config['opener_binary']).resolve()
            if not binary.is_relative_to(ROOT):
                raise ValueError('RELEASE_LOCAL_OPENER_BINARY_REQUIRED')
            adapter = OpenerProcess(binary, config['opener_binary_sha256'], config['opener_ipc_path'],
                owner_lock=lock,
                approved=config.get('cyclic_transport_activation_approved', False),
                admission=(profile['cycle_admission'] if profile.get('cycle_admission') in
                    ('SUPERVISED_REPEAT_TEST', 'PLC_AUTOMATIC_REPEAT') else 'FIRST_PRODUCT_ONLY'))
        from src.control.opener_cyclic import OpenerGateway
        gateway = (OpenerGateway(config['opener_ipc_path'], writes_enabled=config.get('cyclic_publication_enabled', False))
                   if contract == 'OPENER_CYCLIC' else LegacyStandaloneGateway(config['plc_ip'], config['plc_local_ip'],
                   writes_enabled=config.get('legacy_publication_enabled', False))
                   if contract == 'LEGACY_THREE_BOOL' else LineGateway(config['plc_ip'], config['plc_local_ip']))
        assembly = ProcessAssemblyInspector(config['data_root'], config['data_root']/'assembly', assets_root=assets)
        runtime = build_runtime(config['package'], station, config['data_root'], mode='production',
            production_gateway=gateway, inspection_motion_mode='STATIONARY',
            standalone_profile=profile, assembly=assembly)
        identity.update(line_session_id=runtime.handshake.session_id,
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
        runtime._event(dict(event='STANDALONE_SERVICE_STARTED', identity=identity))
        app = create_integrated_app(runtime, {config['package'].name: config['package']})
        close_adapter_on_shutdown(app, adapter)
        configure_line_web(app, runtime, identity)
        uvicorn.run(app, host=config['listen_host'], port=config['port'], log_level='warning', access_log=False)
    finally:
        close_resources(runtime, assembly, gateway, adapter, lock)


if __name__ == '__main__':
    main()
