import importlib.util
from pathlib import Path
from .models import App, Firmware

def build(app_id: int, firmware_id: int, branch: str = "main") -> str:
    """Build an app by its id and returns the path to the built .fap file"""
    app_object = App.objects.filter(id=app_id).first()
    if not app_object:
        raise ValueError(f'App with id {app_id} not found')
    firmware_object = Firmware.objects.filter(id=firmware_id).first()
    if not firmware_object:
        raise ValueError(f'Firmware with id {firmware_id} not found')
    
    _spec = importlib.util.spec_from_file_location(
        "main", Path(__file__).resolve().parent.parent / "flipperzero-ufbt-app" / "main.py"
    )
    _main = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_main)
    _map = {
        "official": _main.FIRMWARE_OFFICIAL,
        "momentum": _main.FIRMWARE_MOMENTUM,
        "unleashed": _main.FIRMWARE_UNLEASHED,
        "rogue_master": _main.FIRMWARE_ROGUE_MASTER,
    }
    return _main.fetch_and_build_url(app_object.location_origin, branch, _map.get(firmware_object.firmware_id, _main.FIRMWARE_OFFICIAL))