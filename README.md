# Docker Volume Backup

This is just a simple python cli to backup docker volumes to Azure Storage.

### Installation

1. Clone the repository
```bash
git clone https://github.com/madalinpopa/volume-backup.git
```

2. Switch directory to repository and install.
```bash
pip3 install .
```
3. Export the following environment variables

```bash
# Azure storage account name
export AZURE_STORAGE_ACCOUNT_NAME=your-storage-account

# Azure storage container
export AZURE_STORAGE_CONTAINER=your-storage-container
```

### Usage

```bash
volume-backup --container nginx --upload
```
