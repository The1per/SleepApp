import os, sys, docker, subprocess, platform
import pandas as pd
from typing import List, Tuple, Set

def list_images(client: docker.DockerClient) -> None:
    try:
        images = client.images.list()
        if not images:
            print("No Docker images found.", flush=True)
            return

        print("Available Docker Images:", flush=True)
        for image in images:
            tags = ', '.join(image.tags) if image.tags else "<untagged>"
            print(f"Image ID: {image.id[:12]} | Tags: {tags}", flush=True)
    except Exception as e:
        print(f"Error communicating with Docker daemon: {e}", flush=True)

def match_images_to_tasks(client: docker.DockerClient, tasks: List[str]) -> List[Tuple[str, str]]:
    matches, missing = [], set()
    try:
        images = client.images.list()
    except Exception:
        return missing

    for task in tasks:
        task_image_name = f'caisr_{task}'
        task_found = False
        for image in images:
            for tag in image.tags:
                if tag == f'{task_image_name}:latest' or tag.split(':')[0] == task_image_name:
                    matches.append((task, tag))
                    task_found = True
                    break 
            if task_found: break 
        if not task_found: missing.add(task)

    if len(missing) > 0:
        images = install_missing_dockers(client, tasks, missing)
    return matches

def install_missing_dockers(client: docker.DockerClient, tasks: List[str], missing: Set[str]) -> List[Tuple[str, str]]:
    print("  Installing missing Dockers:", flush=True)
    for task in missing:
        zipped_image = os.path.join('.', 'dockers', f"{task}.tar.gz")
        try:
            print(f"Loading Docker image for task '{task}' from {zipped_image}...", flush=True)
            subprocess.check_call(["docker", "load", "-i", zipped_image])
        except Exception as e:
            print(f"Error installing Docker image '{task}': {e}", flush=True)
            sys.exit(1)
    return match_images_to_tasks(client, tasks)

def set_run_parameters(data_folder: str, tasks: List[str]) -> None:
    param_folder = os.path.join(data_folder, 'run_parameters')
    os.makedirs(param_folder, exist_ok=True)
    for task in tasks:
        params_df = pd.DataFrame()
        params_df.loc[0, 'overwrite'] = True
        if task == 'preprocess':
            params_df.loc[0, 'overwrite'] = False
            params_df.loc[0, 'autoscale_signals'] = True
        csv_path = os.path.join(param_folder, f'{task}.csv')
        params_df.to_csv(csv_path, index=False, mode='w+')

def run_python_script_in_docker(image_name: str, task: str, data_folder: str, caisr_output_folder: str) -> None:
    data_folder = os.path.abspath(data_folder)
    caisr_output_folder = os.path.abspath(caisr_output_folder)

    if platform.system().lower() == 'windows':
        data_folder = data_folder.replace('\\', '/').replace(':', '')
        caisr_output_folder = caisr_output_folder.replace('\\', '/').replace(':', '')
        data_mount = f"/{data_folder[0]}{data_folder[1:]}:/data/data/"
        output_mount = f"/{caisr_output_folder[0]}{caisr_output_folder[1:]}:/data/caisr_output/"
        prompt = ["docker", "run", "--rm", "-v", data_mount, "-v", output_mount, image_name]
    else:
        data_mount = f"{data_folder}:/data/data/"
        output_mount = f"{caisr_output_folder}:/data/caisr_output/"
        prompt = ["docker", "run", "-it", "--rm", "-v", data_mount, "-v", output_mount, image_name]
        
    print(f"\n--> Booting Docker '{task}' with image '{image_name}'", flush=True)
    try:
        subprocess.check_call(prompt)
    except Exception as e:
        print(f"Error occurred while executing '{task}' in Docker: {e}", flush=True)

# === НОВАЯ ФУНКЦИЯ ДЛЯ ВЫЗОВА ИЗ БРИДЖА ===
def run_docker_pipeline(base_dir: str):
    tasks = ['stage']
    data_folder = os.path.join(base_dir, 'data')  
    caisr_output_folder = os.path.join(base_dir, 'caisr_output') 

    try:
        client = docker.from_env()
        list_images(client)
        images = match_images_to_tasks(client, tasks)
        set_run_parameters(data_folder, tasks)

        for task, (_, image_name) in zip(tasks, images):
            if task in ['stage', 'limb']:
                intermediate_folder = os.path.join(caisr_output_folder, 'intermediate', task)
                os.makedirs(intermediate_folder, exist_ok=True)
            run_python_script_in_docker(image_name, task, data_folder, caisr_output_folder)
            
        print(f"Completed running all specified tasks: {tasks}", flush=True)
    except Exception as e:
        print(f"Docker pipeline initialization failed: {e}")

if __name__ == '__main__':
    run_docker_pipeline(os.getcwd())