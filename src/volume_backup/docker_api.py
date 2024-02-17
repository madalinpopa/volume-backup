from docker import DockerClient
from docker.errors import NotFound
from docker.models.containers import Container

from .custom_logger import get_logger

logger = get_logger(__name__)


Volumes = list[tuple[str, str]]


class DockerAPIWrapper:

    def __init__(self):
        self.client = DockerClient().from_env()

    def get_container_volumes(self, container_name: str) -> Volumes | None:
        """
        Retrieves the volumes associated with a given container.

        Args:
            container_name (str): The name of the container.

        Returns:
            Volumes | None: A list of tuples containing the name and destination of each volume,
            or None if the container is not found.
        """
        try:
            container: Container = self.client.containers.get(container_name)
            return [
                (mount["Name"], mount["Destination"])
                for mount in container.attrs["Mounts"]
                if mount["Type"] == "volume"
            ]
        except NotFound:
            logger.error(f"Container: {container_name} not found")

    def create_tar_files(
        self, host_path: str, volumes_from: str, command: str
    ):
        """
        Creates tar files for the specified container volumes.

        Args:
            host_path (str): The path on the host where the tar files will be created.
            volumes_from (str): The name or ID of the container from which to backup volumes.
            command (str): The command to execute inside the container.

        Returns:
            str: The output of the container run command.
        """

        logger.info(f"Backing up volumes for container: {volumes_from}")
        return self.client.containers.run(
            auto_remove=True,
            detach=True,
            volumes_from=[volumes_from],
            volumes=[f"{host_path}:/backup:rw"],
            image="busybox",
            command=command,
        )
