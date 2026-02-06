from datetime import datetime
import requests
import json
import uuid
import os
from time import time


class ELNClient:
    def __init__(self, user_file='Client.json') -> None:
        self.USER = json.load(open(user_file))

        self.TOKEN_URL = "https://eln.iphy.ac.cn:61262/tokens"
        self.REFRESHTOKEN_URL = "https://eln.iphy.ac.cn:61262/tokens/tokens_refresh"
        self.UPLOAD_URL = "https://eln.iphy.ac.cn:61262/eln_api/upload"
        self.UPDATE_URL = "https://eln.iphy.ac.cn:61262/eln_api/update"
        self.IMPORT_URL = "https://eln.iphy.ac.cn:61262/eln_api/import"

        self.ELN_NAME = "亚毫开系统运行记录-电子版"
        self.RECORD_UID = "TU6TDN57QH30P12T"

        # runtime state
        self.ACCESS_TOKEN = None

        # ids used by add_file_to_form
        self.note_id = None
        self.files_id = None

    # ------------------------------------------------------------------
    # Token
    # ------------------------------------------------------------------
    def get_token(self):
        resp = requests.post(
            self.TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "username": self.USER["UserName"],
                "password": self.USER["pw"],
            },
        )
        data = resp.json()
        if data.get("errcode") != 0:
            raise RuntimeError(f"Token error: {data}")
        self.ACCESS_TOKEN = data["access"]["token"]

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------
    def _post_json(self, url, payload):
        content = {
            "url": url,
            "headers": {
                "Authorization": f"Bearer {self.ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            "data": json.dumps(payload, ensure_ascii=False),
        }
        resp = requests.post(**content).json()
        if resp.get("code") == 5:
            self.get_token()
            resp = requests.post(**content).json()
        return resp

    def _post_file(self, url, payload, files):
        content = {
            "url": url,
            "headers": {"Authorization": f"Bearer {self.ACCESS_TOKEN}"},
            "data": payload,
            "files": files
        }
        resp = requests.post(**content).json()
        if resp.get("code") == 5:
            self.get_token()
            resp = requests.post(**content).json()
        return resp
        
    # ------------------------------------------------------------------
    # Record
    # ------------------------------------------------------------------
    def new_record(self, name='Demag_2026-02-03', Description='Demag'):
        TEMPLATE_NAME = "C1-Demagnetization"
        uid = str(uuid.uuid4())

        payload = {
            "eln": self.ELN_NAME,
            "template": TEMPLATE_NAME,
            "dataset": [{
                "title": name,
                "uid": uid,
                "data": {
                    "Basic Infomation": {
                        "Date created": datetime.now().strftime("%Y-%m-%d"),
                        "Description": Description,
                    },
                }
            }]
        }

        self._post_json(self.IMPORT_URL, payload)
        self.RECORD_UID = uid
        print(f"record created with uid: {uid}")

    # ------------------------------------------------------------------
    # File upload
    # ------------------------------------------------------------------
    def _upload_file_auto(self, file_path, chunk_size=10 * 1024 * 1024):
        file_size = os.path.getsize(file_path)
        uid = str(uuid.uuid4())

        base = os.path.basename(file_path)
        name, _ = os.path.splitext(base)
        file_name = f"{name}_{str(uuid.uuid4())[:8]}"
        upload_resp = {}

        if file_size <= chunk_size:
            with open(file_path, "rb") as f:
                upload_resp = self._post_file(
                    self.UPLOAD_URL,
                    {"uid": uid, "name": file_name, "last": "1"},
                    [("file", (base, f))]
                )
        else:
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    last = "1" if f.tell() == file_size else "0"
                    upload_resp = self._post_file(
                        self.UPLOAD_URL,
                        {"uid": uid, "name": file_name, "last": last},
                        [("file", (base, chunk))]
                    )
        return upload_resp, file_name

    # ------------------------------------------------------------------
    # Form: add note + files
    # ------------------------------------------------------------------
    def add_file_to_form(self, module, note, file_paths, method='add'):
        if not note:
            raise ValueError("note is empty")
        if not file_paths:
            raise ValueError("file path is empty")

        file_names = [
            self._upload_file_auto(p)[1]
            for p in file_paths
        ]

        if method == 'add':
            self.note_id = f"note_{int(time())}"
            self.files_id = f"files_{int(time())}"

            payload = {
                "eln": self.ELN_NAME,
                "uid": self.RECORD_UID,
                "add": [
                    {
                        "module": module,
                        "name": self.note_id,
                        "type": "richtext",
                        "data": note,
                    },
                    {
                        "module": module,
                        "name": self.files_id,
                        "type": "file",
                        "data": [f"#file{{{n}}}" for n in file_names],
                    }
                ]
            }
        else:
            payload = {
                "eln": self.ELN_NAME,
                "uid": self.RECORD_UID,
                "modify": [
                    {
                        "path": [module, self.note_id],
                        "data": note,
                    }
                ]
            }

        self._post_json(self.UPDATE_URL, payload)

    # ------------------------------------------------------------------
    # Table
    # ------------------------------------------------------------------
    def add_table(self):
        self.table_name = "Phase Transition Points"
        payload = {
            "eln": self.ELN_NAME,
            "uid": self.RECORD_UID,
            "addModule": [{
                "name": self.table_name,
                "type": "table"
            }],
            "add": [
                {"module": self.table_name, "type": "text", "name": "name"},
                {"module": self.table_name, "type": "text", "name": "time"},
                {"module": self.table_name, "type": "text", "name": "field"},
                {"module": self.table_name, "type": "text", "name": "C"},
            ]
        }
        self._post_json(self.UPDATE_URL, payload)

    def add_data_to_table(self, data):
        payload = {
            "eln": self.ELN_NAME,
            "uid": self.RECORD_UID,
            "add": [{
                "module": self.table_name,
                "row": -1,
                "data": []
            }],
            "modify": [
                {"path": [self.table_name, "name", -1], "data": str(data[0])},
                {"path": [self.table_name, "time", -1], "data": str(data[1])},
                {"path": [self.table_name, "field", -1], "data": str(data[2])},
                {"path": [self.table_name, "C", -1], "data": str(data[3])},
            ]
        }
        result = self._post_json(self.UPDATE_URL, payload)
        if result.get('code') == 4:
            payload_colnames = {
            "eln": self.ELN_NAME,
            "uid": self.RECORD_UID,
            "add": [
                {"module": self.table_name, "type": "text", "name": "name"},
                {"module": self.table_name, "type": "text", "name": "time"},
                {"module": self.table_name, "type": "text", "name": "field"},
                {"module": self.table_name, "type": "text", "name": "C"},
            ],}
            result = self._post_json(self.UPDATE_URL, payload_colnames)
            result = self._post_json(self.UPDATE_URL, payload)
        return result

    # ------------------------------------------------------------------
    # Richtext image
    # ------------------------------------------------------------------
    def build_file_url(self, upload_resp):
        return f"elnurl://{upload_resp['query']}"

    def add_images_to_richtext(self, module, image_paths, notes):
        data = ''
        for image_path, note in zip(image_paths, notes):
            upload_resp = self._upload_file_auto(image_path)
            # upload response not needed, URL is built by name
            image_url = upload_resp[0]['query']
            image_url = f"elnurl://{image_url}"
            data += f"<p>{note}</p><p><img src=\"{image_url}\" /></p><br>"
        payload = {
            "eln": self.ELN_NAME,
            "uid": self.RECORD_UID,
            "modify": [{
                "path": [module],
                "data": data
            }]
        }
        self._post_json(self.UPDATE_URL, payload)

    # ------------------------------------------------------------------
    # File collections
    # ------------------------------------------------------------------

    def add_file_module(self, module: str):
        payload = {
            "eln": self.ELN_NAME,
            "uid": self.RECORD_UID,
            "addModule": [{
                "name": module,
                "type": "files"
            }]
        }

        self._post_json(self.UPDATE_URL, payload)
    
    def add_files(self, module: str, file_paths: list, notes=['']):
        file_names = [
            self._upload_file_auto(p)[1]
            for p in file_paths
        ]
        for file_name, note in zip(file_names, notes):
            
            payload = {
                "eln": self.ELN_NAME,
                "uid": self.RECORD_UID,
                "add": [{
                    "module": module,
                    "data": {"file": f"#file{{{file_name}}}", "text": note}
                }]
            }

            result = self._post_json(self.UPDATE_URL, payload)
        return result
        
    def add_operation(self, key='', operation='Operation', t='', module='Key Operations'):
        if len(t) == 0:
            t = datetime.now().strftime("%Y-%m-%d %H:%M")
        Operation_date, Operation_time = t.split(' ')
        row = [
                {"path": [module, 'Date', -1], "data": Operation_date},
                {"path": [module, 'Time', -1], "data": Operation_time},
                {"path": [module, 'Keyword', -1], "data": key},
                {"path": [module, 'Operation', -1], "data": operation},
            ]
        data = f'{t}:    {operation}'
        # print(data)
        payload = {
            "eln": self.ELN_NAME,
            "uid": self.RECORD_UID,
            "add": [{
                "module": module,
                "row": -1,
                "data": []
            }],
            "modify": row
        }
        return self._post_json(self.UPDATE_URL, payload)
        