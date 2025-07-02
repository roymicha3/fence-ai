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
    
    first_image_name = "first_image.jpg"
    second_image_name = "second_image.jpg"
    text_name = "prompt.txt"

    first_image_src_path = os.path.join(source_dir, first_image_name)
    second_image_src_path = os.path.join(source_dir, second_image_name)
    text_src_path = os.path.join(source_dir, text_name)

    first_image_dest_path = os.path.join(remote_dir, first_image_name)
    second_image_dest_path = os.path.join(remote_dir, second_image_name)
    text_dest_path = os.path.join(remote_dir, text_name)

    backend.upload_file(Path(first_image_src_path), first_image_dest_path)
    backend.upload_file(Path(second_image_src_path), second_image_dest_path)
    backend.upload_file(Path(text_src_path), text_dest_path)
    
    invoke_cfg = load_config("configs/n8n_config.yaml")
    
    payload = load_json_payload(invoke_cfg.payload_path)
    
    payload["session_prefix"] = remote_dir
    payload["images"] = [first_image_name, second_image_name]
    payload["text_file_name"] = text_name

    print(payload)

    invoker = N8NInvoker(invoke_cfg)
    
    response = invoker.invoke(payload)
    
    print_response_info(response)
    
    

    backend.delete_file(first_image_dest_path)
    backend.delete_file(second_image_dest_path)
    backend.delete_file(text_dest_path)