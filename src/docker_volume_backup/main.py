# https://docs.docker.com/storage/volumes/#back-up-restore-or-migrate-data-volumes
import logging
import os
from datetime import datetime

from docker import DockerClient
from docker.errors import NotFound
from docker.models.containers import Container

# Docker socket
DOCKER_HOST_URL = "unix://var/run/docker.sock"

# Docker container used to create the backup for volumes
BACKUP_CONTAINER_IMAGE = "busybox"

# The local path where to store the backup files
BACKUP_STORAGE = "/Users/madalinpopa/backup"


class DockerManager:
    def __init__(self, client: DockerClient):
        self.client = client
        self.tar_files: list[str] = []
        self.backup_storage = BACKUP_STORAGE
        self.backup_container_image = BACKUP_CONTAINER_IMAGE

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def _get_container_volume_details(self, container_name: str) -> dict:
        """Retrieve volume details of a given container."""
        try:
            container = self.client.containers.get(container_name)
            return {
                "container_name": container_name,
                "volumes": [
                    (mount["Name"], mount["Destination"])
                    for mount in container.attrs["Mounts"]
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

    def backup(self, container_name: str):
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


def main():
    """
    This is the main function of the backup application.
    It is responsible for executing the backup process.
    """
    client = DockerClient(base_url=DOCKER_HOST_URL)

    with DockerManager(client=client) as manager:
        manager.backup("nginx")


if __name__ == "__main__":
    main()
