import argparse
import os
from datetime import datetime

from .azure_api import AzureStorageAPIWrapper
from .custom_logger import get_logger
from .docker_api import DockerAPIWrapper

# Create a logger
logger = get_logger(__name__)


class BackupManager:
    """
    A class that manages the backup of volumes for Docker containers.
    """

    def __init__(self):
        self.docker_api = DockerAPIWrapper()
        self._volumes_folder: str
        self._volume_files = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.docker_api.client.close()

    def _generate_tar_command(self, volumes: list[tuple[str]]) -> list[str]:
        """
        Generate a list of tar commands to backup volumes.

        Args:
            volumes (list[tuple[str]]): A list of tuples containing the name and destination of each volume.

        Returns:
            list[str]: A list of tar commands to backup the volumes.
        """
        commands = []
        for name, destination in volumes:
            timestamp = datetime.now().strftime("%Y%m%d%H%M")
            filename = f"{name}-{timestamp}.tar"
            fullpath = f"/backup/{filename}"
            tar_cmd = f"tar cvf {fullpath} {destination}"
            commands.append(tar_cmd)
            self.volume_files.append(filename)
        return commands

    def _generate_backup_folder(self, container_name: str) -> str:
        """
        Create a folder in current directory with container name to store the volume backup.

        Args:
            container_name (str): The name of the container.

        Returns:
            str: The full path of the backup folder.
        """
        current_directory = os.getcwd()
        full_path = os.path.join(current_directory, container_name)
        os.makedirs(full_path, exist_ok=True)
        self.volumes_folder = full_path
        return full_path

    def backup(self, container_name: str):
        """
        Backup the volumes of a Docker container.

        Args:
            container_name (str): The name of the Docker container.

        Returns:
            None
        """

        volumes = self.docker_api.get_container_volumes(container_name)
        commands = self._generate_tar_command(volumes=volumes)
        host_path = self._generate_backup_folder(container_name)
        for cmd in commands:
            self.docker_api.create_tar_files(
                host_path=host_path,
                volumes_from=container_name,
                command=cmd,
            )

    def upload(self, container_name: str):
        storage = AzureStorageAPIWrapper()
        for volume_file in self._volume_files:
            tar_file = os.path.join(self._volumes_folder, volume_file)
            storage.upload(tar_file, container_name)


def main():
    parser = argparse.ArgumentParser(
        prog="volume-backup",
        description="Docker volume backup tool",
    )
    parser.add_argument(
        "-c",
        "--container",
        type=str,
        help="Container name",
        required=True,
    )

    parser.add_argument(
        "-u",
        "--upload",
        action="store_true",
        help="Upload to Azure Storage",
        required=False,
    )

    args = parser.parse_args()

    with BackupManager() as manager:
        manager.backup(args.container)
        if args.upload:
            manager.upload(args.container)


if __name__ == "__main__":
    main()
