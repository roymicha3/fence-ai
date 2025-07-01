from pathlib import Path
import os
import sys
from storage.providers.s3_backend import S3Backend
from botocore.exceptions import BotoCoreError, ClientError

from invoker.invoke_config import load_config
from invoker.invoker import N8NInvoker
from invoker.payload_utils import load_json_payload, save_json_response
from invoker.response_parser import print_response_info

STORAGE_PATHS = \
    {
        "cred_src": "creds/Server_accessKeys.csv",
        "cfg_src": "configs/bucket.yaml"
    }


if __name__ == "__main__":
    backend = S3Backend(**STORAGE_PATHS)

    # upload file

    remote_dir = "test"
    source_dir = "res"
    
    image_name = "test.jpg"
    text_name = "test.txt"

    image_src_path = os.path.join(source_dir, image_name)
    text_src_path = os.path.join(source_dir, text_name)

    image_dest_path = os.path.join(remote_dir, image_name)
    text_dest_path = os.path.join(remote_dir, text_name)

    backend.upload_file(Path(image_src_path), image_dest_path)
    backend.upload_file(Path(text_src_path), text_dest_path)
    
    invoke_cfg = load_config("configs/n8n_config.yaml")
    
    payload = load_json_payload(invoke_cfg.payload_path)
    
    payload["session_prefix"] = remote_dir
    payload["image_name"] = image_name
    payload["text_file_name"] = text_name

    print(payload)

    invoker = N8NInvoker(invoke_cfg)
    
    response = invoker.invoke(payload)
    
    print_response_info(response)

    backend.delete_file(image_dest_path)
    backend.delete_file(text_dest_path)