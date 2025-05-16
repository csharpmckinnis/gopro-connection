import asyncio
from open_gopro import WirelessGoPro
from box_sdk_gen import BoxClient, BoxDeveloperTokenAuth, BoxCCGAuth, CCGConfig, UploadFileAttributes, UploadFileAttributesParentField, CreateCollaborationItem, CreateCollaborationItemTypeField, CreateCollaborationAccessibleBy, CreateCollaborationAccessibleByTypeField, CreateCollaborationRole, AddShareLinkToFileSharedLink, AddShareLinkToFileSharedLinkAccessField, CreateFileMetadataByIdScope, GetMetadataTemplateScope
import dotenv
import os

# Load environment variables from .env file
dotenv.load_dotenv()

# Access the Box credentials
BOX_DEV_TOKEN = os.getenv("BOX_DEV_TOKEN")
BOX_CLIENT_ID = os.getenv("BOX_CLIENT_ID")
BOX_CLIENT_SECRET = os.getenv("BOX_CLIENT_SECRET")
BOX_ENTERPRISE_ID = os.getenv("BOX_ENTERPRISE_ID")

class Box():
    def __init__(self, client_id=None, client_secret=None, enterprise_id=None):
        self.client_id = client_id or BOX_CLIENT_ID
        self.client_secret = client_secret or BOX_CLIENT_SECRET
        self.enterprise_id = enterprise_id or BOX_ENTERPRISE_ID
        self.client = None
        self.auth = None
        self.videos_folder_box_id = '303832684570'
        self.box_road_health_folder_id = '309237796489'
        self.box_metadata_template_key = "folderWatcherMetadata"

        self.authenticate()
        print(f"{self.client = }")     
        
    ## SECURITY AND AUTHENTICATION

    def authenticate(self):
        """
        Authenticates the client using the Client Credentials Grant (CCG) flow.
        """
        try:
            # Set up CCG-based authentication
            ccg_config = CCGConfig(
                client_id=self.client_id,
                client_secret=self.client_secret,
                enterprise_id=self.enterprise_id
            )
            self.auth = BoxCCGAuth(config=ccg_config)
            self.client = BoxClient(auth=self.auth)
            print('Authenticated with Box using CCG flow.')
        except Exception as e:
            print(f"Error during authentication: {e}")
            raise
        
    def test_connection(self):
        """
        Tests the connection by retrieving items from the root folder.
        """
        try:
            root_folder = self.client.folders.get_folder_by_id('0')
            print(f"Connected to Box as: {self.client}")

            # Retrieve and log items in the root folder
            for item in root_folder.item_collection.entries:
                print(f"- {item.type.capitalize()} | Name: {item.name} | ID: {item.id}")
        except Exception as e:
            print(f"Error testing connection: {e}")

    def upload_small_file_to_folder(self, file_path, folder_id="0", new_name=None):
        """
        Uploads a <50MB file to the specified folder.
        Args:
            file_path (str): The local path to the file to upload.
            folder_id (str): The ID of the folder to upload to.
        Returns:
            dict: Information about the uploaded file.
        """
        try:
            if not new_name:
                new_file_name = os.path.basename(file_path)
            else:
                new_file_name = new_name
            
            with open(file_path, "rb") as file:
                uploaded_file = self.client.uploads.upload_file(
                    UploadFileAttributes(
                        name=new_file_name, parent=UploadFileAttributesParentField(id=folder_id)
                    ),
                    file,
                )
        
                return uploaded_file
        except Exception as e:
            print(f"Failed to upload file '{file_path}': {e}")
            return None
    
    def upload_large_file_to_folder(self, file_path, file_name, parent_folder_id):
        """Uploads a large file using the Box Gen SDK's `upload_big_file()` method."""
        
        file_size = os.path.getsize(file_path)

        try:
            with open(file_path, 'rb') as file_stream:
                uploaded_file = self.client.chunked_uploads.upload_big_file(
                    file=file_stream,
                    file_name=file_name,
                    file_size=file_size,
                    parent_folder_id=parent_folder_id
                )

            return uploaded_file

        except Exception as e:
            print(f"Error uploading file '{file_name}': {e}")
            return None
    
    def get_file_size(self, file_path):
        return os.path.getsize(file_path)
    
    def upload_file_to_box(self, source_file_path, dest_file_name, dest_folder_id): 
        """
        Uploads a file to Box, handling small and large files differently.
        Args:
            source_file_path (str): The local path to the file to upload.
            dest_file_name (str): The name to give the file on Box.
            dest_folder_id (str): The ID of the folder to upload to.
        """
        file_size = self.get_file_size(source_file_path)
        
        if file_size < 20 * 1024 * 1024:
            # Upload small file
            print(f"Uploading small file '{source_file_path}' to Box...")
            uploaded_file = self.upload_small_file_to_folder(source_file_path, dest_folder_id, dest_file_name)
        else: 
            uploaded_file = self.upload_large_file_to_folder(source_file_path, dest_file_name, dest_folder_id)
        
        if uploaded_file:
            print(f"Uploaded file '{uploaded_file.name}' to Box with ID: {uploaded_file.id}")
        
    def upload_all_files_to_box(self, source_folder, dest_folder_id):
        """
        Uploads all files from a local folder to Box.
        Args:
            source_folder (str): The local folder containing files to upload.
            dest_folder_id (str): The ID of the Box folder to upload to.
        """
        for root, _, files in os.walk(source_folder):
            for file_name in files:
                try:
                    file_path = os.path.join(root, file_name)
                    print(f"Uploading '{file_path}' to Box...")
                    self.upload_file_to_box(source_file_path = file_path,dest_file_name=file_name,dest_folder_id=dest_folder_id)
                except Exception as e:
                    print(f"Error uploading file '{file_name}': {e}")


async def main():
    async with WirelessGoPro() as gopro:
        print("Connected to GoPro")

        # Get media list
        resp = await gopro.http_command.get_media_list()
        media_list = resp.data.media

        # Download each file
        for group in media_list:
            for fs in group.file_system:
                path = fs.filename
                local_name = f'to_upload/{path.split("/")[-1]}'
                print(f"Downloading {path} to {local_name}...")
                await gopro.http_command.download_file(camera_file=path, local_file=local_name)
                print(f"Downloaded {local_name}")

        # Delete all media on camera
        print("Deleting all media on camera...")
        await gopro.http_command.delete_all()
        print("All media deleted from camera.")

if __name__ == "__main__":
    #asyncio.run(main())
    box = Box()
    box.upload_all_files_to_box("to_upload", box.videos_folder_box_id)