# https://docs.docker.com/storage/volumes/#back-up-restore-or-migrate-data-volumes
import logging
import os
from datetime import datetime

from docker import DockerClient
from docker.errors import NotFound
from docker.models.containers import Container

from azure.identity import ClientSecretCredential
from azure.storage.blob import BlobServiceClient

from dotenv import load_dotenv

load_dotenv()

# Docker socket
DOCKER_HOST_URL = "unix://var/run/docker.sock"

# Docker container used to create the backup for volumes
BACKUP_CONTAINER_IMAGE = "busybox"

# The local path where to store the backup files
BACKUP_STORAGE = "/Users/madalinpopa/backup"

# ID of a Microsoft Entra application
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")

# ID of the application's Microsoft Entra tenant
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")

# One of the application's client secrets
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")

# Azure storage account name
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")

# Azure storage container
AZURE_STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER")


class DockerManager:
    def __init__(self, client: DockerClient):
        self.client = client
        self.tar_files: list[str] = []
        self.container: Container | None = None
        self.backup_storage = BACKUP_STORAGE
        self.backup_container_image = BACKUP_CONTAINER_IMAGE

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def _get_container_volume_details(self, container_name: str) -> dict:
        """Retrieve volume details of a given container."""
        try:
            self.container = self.client.containers.get(container_name)
            return {
                "container_name": container_name,
                "volumes": [
                    (mount["Name"], mount["Destination"])
                    for mount in self.container.attrs["Mounts"]
                    if mount["Type"] == "volume"
                ],
            }
        except NotFound:
            logging.error(f"Container {container_name} not found")
            raise

    def _run_backup_command(self, command: str, container_name: str) -> Container:
        """Run a backup command in a Docker container."""
        return self.client.containers.run(
            auto_remove=True,
            detach=True,
            volumes_from=[container_name],
            volumes=[f"{self.backup_storage}:/backup:rw"],
            image=self.backup_container_image,
            command=command,
        )

    def _create_container_backup_folder(self, container_name: str) -> str:
        """Create a backup folder for a container."""
        if not os.path.exists(self.backup_storage):
            raise FileNotFoundError()
        full_path = os.path.join(self.backup_storage, container_name)
        os.makedirs(full_path, exist_ok=True)
        return full_path

    def backup(self, container_name: str) -> None:
        """Backup the specified container."""
        try:
            container_details = self._get_container_volume_details(container_name)
            backup_folder = self._create_container_backup_folder(container_name)
            if container_details["volumes"]:
                for volume, destination in container_details["volumes"]:
                    timestamp = datetime.now().strftime("%Y%m%d%H%M")
                    tar_file = f"{volume}-{timestamp}.tar"
                    mount_path = f"/backup/{container_name}/{tar_file}"
                    command = f"tar cvf {mount_path} {destination}"
                    result = self._run_backup_command(command, container_name)
                    if result and result.status == "created":
                        tar_path = os.path.join(backup_folder, tar_file)
                        self.tar_files.append(tar_path)
                logging.info(f"Backup for container {container_name} completed")
            else:
                logging.info(f"Container {container_name} has no volume")
        except Exception as e:
            logging.error(f"Error during backup: {e}")
            raise


class AzureManager:
    def __init__(self, blob_service_client: BlobServiceClient):
        self.blob_service_client = blob_service_client
        self.container = AZURE_STORAGE_CONTAINER

    def upload(self, filename: str, container_name: str) -> None:
        tar_file = os.path.basename(filename)
        blob_name = f"{container_name}/{tar_file}"
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container,
            blob=blob_name,
        )
        with open(filename, "rb") as data:
            blob_client.upload_blob(data)
            logging.info(f"Uploaded volume for container {container_name}")


def get_azure_blob_storage_client() -> BlobServiceClient:
    account_url = f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
    credential = ClientSecretCredential(
        tenant_id=AZURE_TENANT_ID,
        client_id=AZURE_CLIENT_ID,
        client_secret=AZURE_CLIENT_SECRET,
    )
    return BlobServiceClient(
        account_url,
        credential=credential,
    )


def main():
    """
    This is the main function of the backup application.
    It is responsible for executing the backup process.
    """
    client = DockerClient(base_url=DOCKER_HOST_URL)
    blob_service_client = get_azure_blob_storage_client()

    azure_manager = AzureManager(blob_service_client=blob_service_client)

    with DockerManager(client=client) as docker_manager:
        docker_manager.backup("nginx")
        for tar in docker_manager.tar_files:
            azure_manager.upload(tar, docker_manager.container.name)


if __name__ == "__main__":
    main()
