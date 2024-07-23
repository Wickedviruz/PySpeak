import asyncio
import logging
from datetime import datetime

async def backup_database(db_file, backup_folder, backup_interval_minutes):
    while True:
        await asyncio.sleep(backup_interval_minutes * 60)
        backup_file = f"{backup_folder}/backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.db"
        with open(db_file, 'rb') as src, open(backup_file, 'wb') as dst:
            dst.write(src.read())
        logging.info(f"Database backed up to {backup_file}")
