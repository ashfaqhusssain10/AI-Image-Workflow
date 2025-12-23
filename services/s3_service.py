import boto3
import os
import random

class S3Service:
    def __init__(self):
        from botocore.config import Config
        
        region = os.getenv('AWS_REGION', 'ap-south-1')
        my_config = Config(
            region_name = region,
            signature_version = 's3v4',
            s3={'addressing_style': 'virtual'}  # Ensure virtual-hosted style
        )
        
        # Use explicit regional endpoint to ensure signature matches hostname
        endpoint_url = f'https://s3.{region}.amazonaws.com'
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            aws_session_token=os.getenv('AWS_SESSION_TOKEN'),
            config=my_config,
            endpoint_url=endpoint_url
        )
        self.bucket_name = os.getenv('S3_BUCKET_NAME', 'my-reference-images')

    def get_reference_image(self):
        """
        Fetches a random image URL from the bucket.
        If credentials are not found, returns a placeholder.
        """
        try:
            # Check if we can list objects
            print(f"DEBUG: Listing objects in bucket: {self.bucket_name}")
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=100)
            if 'Contents' in response:
                images = [obj['Key'] for obj in response['Contents'] if obj['Key'].lower().endswith(('.png', '.jpg', '.jpeg'))]
                print(f"DEBUG: Found images: {images}")
                if images:
                    selected = random.choice(images)
                    print(f"DEBUG: Selected image key: {selected}")
                    # Generate presigned URL
                    url = self.s3_client.generate_presigned_url('get_object',
                                                              Params={'Bucket': self.bucket_name,
                                                                      'Key': selected},
                                                              ExpiresIn=3600)
                    print(f"DEBUG: Generated URL: {url}")
                    return url
                else:
                    print("DEBUG: No images found in bucket.")
            else:
                print("DEBUG: No contents in bucket response.")
        except Exception as e:
            print(f"S3 Error: {e}")
        
        # Fallback placeholder if S3 fails or not configured
        print("DEBUG: Returning fallback image URL")
        return "https://picsum.photos/seed/polina/800/600"

    def upload_approved_image(self, local_path, object_key):
        """
        Uploads a local image to S3 under the 'approved/' prefix.
        Returns the S3 URL of the uploaded object.
        """
        try:
            full_key = f"approved/{object_key}"
            region = os.getenv('AWS_REGION', 'ap-south-1')
            
            print(f"DEBUG: Uploading {local_path} to s3://{self.bucket_name}/{full_key}")
            
            self.s3_client.upload_file(local_path, self.bucket_name, full_key)
            
            # Return the S3 URL
            s3_url = f"https://{self.bucket_name}.s3.{region}.amazonaws.com/{full_key}"
            print(f"DEBUG: Upload successful! URL: {s3_url}")
            return s3_url
        except Exception as e:
            print(f"S3 Upload Error: {e}")
            import traceback
            traceback.print_exc()
            return None
