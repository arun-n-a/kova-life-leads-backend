from uuid import uuid4
from typing import List, Dict

import boto3

from config import Config_is
from app.services.custom_errors import *


class AmazonServices:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=Config_is.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config_is.AWS_SECRET_ACCESS_KEY,
        )
        # self.s3_resource = boto3.resource(
        #     "s3",
        #     aws_access_key_id=Config_is.AWS_ACCESS_KEY_ID,
        #     aws_secret_access_key=Config_is.AWS_SECRET_ACCESS_KEY,
        # )
    def put_object(self, file_is, path: str, content_type: str) -> bool:
        response = self.s3_client.put_object(
            Bucket=Config_is.S3_BUCKET_NAME,
            Key=path,
            Body=file_is,
            ContentType=content_type
            )
        if response.get('ResponseMetadata', {}).get('HTTPStatusCode', 0) != 200:
            print(response)
            raise InternalError('File upload has been failed, please try again after sometime')
        print(response)
        return True
    
    def delete_s3_object(self, path: str) -> bool:
        """
        Delete an object from s3
        """
        self.s3_client.delete_object(Bucket=Config_is.S3_BUCKET_NAME, Key=path)
        return True

    def acl_file_upload_obj_s3(self, file_object, path: str, content_type: str) -> Dict:
        """
        Upload files to s3
        """
        try:
            response = self.s3_client.put_object(
                Bucket=Config_is.S3_BUCKET_NAME,
                Key=path,
                Body=file_object.read(),
                ACL="public-read",
                ContentType=content_type,
            )
            print(response)
            if response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0) != 200:
                print(response)
                raise InternalError()
        except Exception as e:
            print(f"acl_file_upload_obj_s3 -- {e}")
            raise InternalError()
        return True

    # def file_encoded_uploader(
    #     self, file_is: object, image_type: str, file_path: str) -> bool:
    #     """
    #     Upload base64 images to S3 bucket
    #     """
    #     s3_obj = self.s3_resource.Object(Config_is.S3_BUCKET_NAME, file_path)
    #     s3_obj.put(
    #         Body=base64.b64decode(file_is), ContentType=image_type, ACL="public-read"
    #     )
    #     return True


    def presigned_url(self, file_path: str) -> str:
        response = self.s3_client.generate_presigned_url(
            "get_object", Params={"Bucket": Config_is.S3_BUCKET_NAME, "Key": file_path}
        )
        return response

    def download_s3_object(self, s3_obj_name: str):
        status = self.s3_client.download_file(
            Config_is.S3_BUCKET_NAME, s3_obj_name, uuid4().hex
        )
        print(status)
        return status

    def list_objects(self, prefix: str) -> List:
        objects = self.s3_client.list_objects_v2(
            Bucket=Config_is.S3_BUCKET_NAME, Prefix=prefix, Delimiter="/"
        )
        result = []
        for file_object in objects.get("Contents", []):
            key_is = file_object.get("Key")
            if not key_is.endswith("/"):
                url = self.s3_client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": Config_is.S3_BUCKET_NAME, "Key": key_is},
                    ExpiresIn=43200,
                )
                result.append({"name": key_is.split("/")[-1], "url": url})
        return result
