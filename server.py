import threading
import logging
import json

from flask import Flask, request, jsonify

from utils import deep_remove_nan
from adapters.renogy_rover_mppt import get_info as get_renogy_rover_info
from adapters.jbd_bms import get_info as get_jbd_info

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
lock = threading.Lock()

@app.route('/device_data', methods=['GET'])
def get_device_data():
    logger.info('get_device_data')
    try:
        mac_address = request.args.get('mac_address')
        adapter = request.args.get('adapter')

        if not mac_address or not adapter:
            return jsonify({"success": False, "error": "`mac_address` and `adapter` are required"}, status=400)

        device_data = {}
        with lock:
            if adapter == 'renogy_rover':
                device_data = get_renogy_rover_info(mac_address)
            elif adapter == 'jbd':
                device_data = get_jbd_info(mac_address)

        result = deep_remove_nan(device_data)

        return jsonify(result)
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    logger.info('Starting server...')
    app.run(port=5007)


# def main():
#     # mac_address = '84:c6:92:13:c0:f4'
#     # data = get_renogy_rover_info(mac_address)
#     mac_address = 'A4:C1:38:0B:79:22'
#     data = get_jbd_info(mac_address)
#     print(deep_remove_nan(data))

# if __name__ == '__main__':
#     main()