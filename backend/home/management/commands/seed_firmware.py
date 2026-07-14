from django.core.management.base import BaseCommand
from home.models import Firmware

FIRMWARES = [
    {"firmware_id": "official",     "name": "Official",    "description": "Official firmware",   "my_order": 0, "version": ""},
    {"firmware_id": "momentum",     "name": "Momentum",    "description": "Momentum firmware",   "my_order": 1, "version": ""},
    {"firmware_id": "unleashed",    "name": "Unleashed",   "description": "Unleashed firmware",  "my_order": 2, "version": ""},
    {"firmware_id": "rogue_master", "name": "RogueMaster", "description": "RogueMaster firmware", "my_order": 3, "version": ""},
]

class Command(BaseCommand):
    help = "Ensure the firmware rows exist"

    def handle(self, *args, **opts):
        for fw in FIRMWARES:
            _, created = Firmware.objects.get_or_create(
                firmware_id=fw["firmware_id"], defaults=fw
            )
            self.stdout.write(("created " if created else "exists  ") + fw["firmware_id"])
