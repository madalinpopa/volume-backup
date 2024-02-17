import os

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from .custom_logger import get_logger

logger = get_logger(__name__)

# Azure storage account name
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")

# Azure storage container
AZURE_STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER")

ACCOUNT_URL = f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"


class AzureStorageAPIWrapper:
    """
    Wrapper class for interacting with Azure Blob Storage API.
    """

    def __init__(self) -> None:
        self._credential = DefaultAzureCredential()
        self._container = "backup"
        self.client = BlobServiceClient(
            account_url=ACCOUNT_URL,
            credential=self._credential,
        )

    def upload(self, filepath: str, docker_container_name: str):
        """
        Uploads a file to Azure Blob Storage.

        Args:
            filepath (str): The path of the file to be uploaded.
            docker_container_name (str): The name of the Docker container.

        Returns:
            None
        """
        tar_file = os.path.basename(filepath)
        blob_name = f"{docker_container_name}/{tar_file}"
        blob_client = self.client.get_blob_client(
            container=self._container,
            blob=blob_name,
        )
        with open(filepath, "rb") as data:
            blob_client.upload_blob(data=data, overwrite=True)
            logger.info(f"Uploaded: {tar_file}")
