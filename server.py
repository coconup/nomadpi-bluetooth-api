import logging
import json
import math

from aiohttp import web

from utils import deep_remove_nan

from adapters.renogy_rover_mppt import get_info as get_renogy_rover_info
from adapters.jbd_bms import get_info as get_jbd_info

async def get_info(request):
    try:
        mac_address = request.query.get('mac_address')
        adapter = request.query.get('adapter')

        if not mac_address or not adapter:
            return web.json_response({"success": False, "error": "`mac_address` and `adapter` are required"}, status=400)

        device_data = {}
        if adapter == 'renogy_rover':
            device_data = await get_renogy_rover_info(mac_address)
        elif adapter == 'jbd':
            device_data = await get_jbd_info(mac_address)

        result = deep_remove_nan(device_data)

        return web.json_response(json.dumps(result))
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}", exc_info=True)
        return web.json_response({"success": False, "error": str(e)})

app = web.Application()
app.router.add_get('/device_data', get_info)

if __name__ == '__main__':
    logging.info('starting server')
    web.run_app(app, port=5007)