"""
API calls to Dojot.
"""
import json
from typing import Callable, List, Dict
import sys
import requests
import gevent

from src.config import CONFIG
from src.utils import Utils


LOGGER = Utils.create_logger("api")


class APICallError(Exception):
    """
    Error when trying to call Dojot API.
    """


class DojotAPI():
    """
    Utility class with API calls to Dojot.
    """
    @staticmethod
    def get_jwt() -> str:
        """
        Request a JWT token.
        """
        url = "{0}/auth".format(CONFIG['dojot']['url'])
        LOGGER.info("Retrieving JWT from %s...", url)

        args = {
            "url": url,
            "data": json.dumps({
                "username": CONFIG['dojot']['user'],
                "passwd": CONFIG['dojot']['passwd'],
            }),
            "headers": {
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
        }

        res = DojotAPI.call_api(requests.post, args)

        LOGGER.info("... Retrieved the JWT token")
        return res["jwt"]

    @staticmethod
    def create_devices(jwt: str, template_id: str, total: int, batch: int) -> None:
        """
        Create the devices.

        Parameters:
            jwt: Dojot JWT token
            template_id: template ID to be used by the devices
            n: total number of devices to be created
            batch: number of devices to be created in each iteration
        """
        LOGGER.info("Creating devices...")

        args = {
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer {0}".format(jwt),
            },
        }

        loads = DojotAPI.divide_loads(total, batch)

        for i, load in enumerate(loads):
            args["data"] = json.dumps({
                "templates": [template_id],
                "attrs": {},
                "label": "CargoContainer_{0}".format(i)
            })
            args["url"] = "{0}/device?count={1}&verbose=false".format(CONFIG['dojot']['url'], load)

            DojotAPI.call_api(requests.post, args, False)

        LOGGER.info("... created the devices")

    @staticmethod
    def create_template(jwt: str) -> str:
        """
        Create the default template for test devices.

        Returns the created template ID.
        """
        LOGGER.info("Creating template...")

        args = {
            "url": "{0}/template".format(CONFIG['dojot']['url']),
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer {0}".format(jwt),
            },
            "data": json.dumps({
                "label": "CargoContainer",
                "attrs": [
                    {
                        "label": "timestamp",
                        "type": "dynamic",
                        "value_type": "integer"
                    },
                ]
            }),
        }

        res = DojotAPI.call_api(requests.post, args)

        LOGGER.info("... created the template")
        return res["template"]["id"]

    @staticmethod
    def create_device(jwt: str, template_id: str, label: str) -> str:
        """
        Create a device in Dojot.

        Parameters:
            jwt: JWT authorization.
            template_id: template to be used by the device.
            label: name for the device in Dojot.

        Returns the created device ID.
        """
        LOGGER.info("Creating the device...")

        args = {
            "url": "{0}/device".format(CONFIG['dojot']['url']),
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer {0}".format(jwt),
            },
            "data": json.dumps({
                "templates": [template_id],
                "attrs": {},
                "label": label,
            }),
        }

        res = DojotAPI.call_api(requests.post, args)

        LOGGER.info("... created the template")
        return res["devices"][0]["id"]

    @staticmethod
    def delete_devices(jwt: str) -> None:
        """
        Delete all devices.
        """
        LOGGER.info("Deleting devices...")

        args = {
            "url": "{0}/device".format(CONFIG['dojot']['url']),
            "headers": {
                "Authorization": "Bearer {0}".format(jwt),
            },
        }

        DojotAPI.call_api(requests.delete, args, False)

        LOGGER.info("... deleted devices")

    @staticmethod
    def delete_templates(jwt: str) -> None:
        """
        Delete all templates.
        """
        LOGGER.info("Deleting templates...")

        args = {
            "url": "{0}/template".format(CONFIG['dojot']['url']),
            "headers": {
                "Authorization": "Bearer {0}".format(jwt),
            },
        }

        DojotAPI.call_api(requests.delete, args, False)

        LOGGER.info("... deleted templates")

    @staticmethod
    def get_devices(jwt: str) -> List:
        """
        Retrieves the devices from Dojot.

        Parameters:
            jwt: Dojot JWT token

        Returns a list of IDs.
        """
        LOGGER.info("Retrieving devices...")

        args = {
            "url": "{0}/device?page_size={1}".format(
                CONFIG['dojot']['url'],
                CONFIG['dojot']['api']['page_size'],
            ),
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer {0}".format(jwt),
            },
        }

        devices_ids = []

        res = DojotAPI.call_api(requests.get, args)

        for i in range(res['pagination']['total']):
            args['url'] = "{0}/device?idsOnly=true&page_size={1}&page_num={2}".format(
                CONFIG['dojot']['url'],
                CONFIG['dojot']['api']['page_size'],
                i + 1
            )

            res = DojotAPI.call_api(requests.get, args)

            devices_ids.extend(res)

        LOGGER.info("... retrieved the devices")

        return devices_ids

    @staticmethod
    def generate_certificate(jwt: str, csr: str) -> str:
        """
        Generate the certificates.

        Parameters:
            jwt: Dojot JWT token
            username: dojot username
            passwd: dojot user password
            csr: CSR in PEM format

        Returns the raw certificate.
        """
        args = {
            "url": CONFIG['dojot']['url'] + "/x509/v1/certificates",
            "headers": {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": "Bearer {0}".format(jwt),
            },
            "data": json.dumps({
                "csr": csr
            }),
        }

        res = DojotAPI.call_api(requests.post, args)

        return (res['certificateFingerprint'], res['certificatePem'])

    @staticmethod
    def revoke_certificate(jwt: str, fingerprint: str) -> None:
        """
        Revoke a certificate.

        Params:
            jwt: Dojot JWT token
            username: dojot username
            status: status to be set, defaults to 10
        """
        args = {
            "url": CONFIG['dojot']['url'] + "/x509/v1/certificates/"+ fingerprint,
            "headers": {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": "Bearer {0}".format(jwt),
            }
        }

        DojotAPI.call_api(requests.delete, args, False)

    @staticmethod
    def retrieve_ca_cert(jwt: str) -> str:
        """
        Retrieves the CA certificate.

        Params:
            jwt: Dojot JWT token

        Returns the CA certificate.
        """
        LOGGER.info("Retrieving the CA certificate...")

        args = {
            "url": f"{CONFIG['dojot']['url']}/x509/v1/ca",
            "headers": {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": "Bearer {0}".format(jwt),
            }
        }

        res = DojotAPI.call_api(requests.get, args)

        if res["caPem"] is None:
            LOGGER.error("Error while retrieving the CA certificate.")
            sys.exit(1)

        certificate = res["caPem"]
        LOGGER.info("... CA certificate retrieved")

        return certificate

    @staticmethod
    def divide_loads(total: int, batch: int) -> List:
        """
        Divides `n` in a list with each element being up to `batch`.
        """
        loads = []

        if total > batch:
            iterations = total // batch
            exceeding = total % batch
            # This will create a list with the number `batch` repeated `iterations` times
            # and then `exceeding` at the final
            loads = [batch] * iterations
            if exceeding > 0:
                loads.append(exceeding)

        else:
            loads.append(total)

        return loads

    @staticmethod
    def call_api(func: Callable[..., requests.Response], args: dict, return_json: bool = True) ->\
        Dict:
        """
        Encapsulates HTTP calls to dojot adding error handling and retrying. Made to use the
        `requests` lib.

        Parameters:
            func: function to call Dojot API (e.g. requests.get).
            args: dictionary of arguments to `func`

        Returns the response in a dictionary
        """
        for _ in range(CONFIG['dojot']['api']['retries'] + 1):
            res = None
            try:
                res = func(**args)
                res.raise_for_status()

            except Exception as exception:
                if res is not None and res.status_code == 429:
                    LOGGER.error("reached maximum number of requisitions to Dojot")
                    sys.exit(1)
                else:
                    LOGGER.error(str(exception))

                gevent.sleep(CONFIG['dojot']['api']['time'])

            else:
                if return_json:
                    return res.json()
                return

        raise APICallError("exceeded the number of retries to {0}".format(args['url']))
