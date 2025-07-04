from pathlib import Path
import os
import sys
from storage.providers.s3_backend import S3Backend
from botocore.exceptions import BotoCoreError, ClientError

from omegaconf import OmegaConf

from invoker.invoker import N8NInvoker
from invoker.payload_utils import load_json_payload, save_json_response
from invoker.response_parser import print_workflow_response
from invoker.save_utils import save_workflow_output
from session.session import Session


def run_session(session: Session) -> None:
    # Load configuration
    config = OmegaConf.load(session.data_dir / "config.yaml")
    
    # Validate config structure
    if not hasattr(config, "storage") or not hasattr(config.storage, "s3"):
        raise ValueError("Config missing required storage.s3 section")
    
    if not hasattr(config, "workflow") or not hasattr(config.workflow, "n8n"):
        raise ValueError("Config missing required workflow.n8n section")
    
    # Initialize backend with .env and specific config section
    backend = S3Backend(env_file=".env", config=config.storage.s3)

    # upload file

    # local directory for saving workflow output
    session_local_dir = session.prefix / Path("outputs")
    session_local_dir.mkdir(parents=True, exist_ok=True)

    remote_dir = Path(session.prefix)  # S3 key prefix
    source_dir = session.data_dir / "res"
    
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
    
    # Get n8n workflow configuration
    workflow_cfg = config.workflow.n8n
    
    # Convert to dict for compatibility
    workflow_cfg_dict = OmegaConf.to_container(workflow_cfg)
    
    payload = load_json_payload(workflow_cfg.payload_path)
    
    payload["session_prefix"] = remote_dir
    payload["images"] = [first_image_name, second_image_name]
    payload["text_file_name"] = text_name

    print(payload)

    invoker = N8NInvoker(workflow_cfg_dict)
    
    response = invoker.invoke(payload)
    
    print_workflow_response(response)
    
    # Save response and images to session directory
    save_results = save_workflow_output(response, session_local_dir)
    print(f"\nSaved response and images to: {save_results['session_dir']}")
    print(f"Images saved: {save_results['image_count']}")
    
    backend.delete_file(first_image_dest_path)
    backend.delete_file(second_image_dest_path)
    backend.delete_file(text_dest_path)
    


if __name__ == "__main__":
    
    parent_session = Session(name="test_session")
    
    # start session
    session = Session(parent=parent_session,
                      resources=[Path("res"), Path("config.yaml")])
    
    run_session(session)