"""
S3ファイルアップロード用ユーティリティ
AWS認証情報は環境変数またはlocal.settings.jsonから取得
"""
import os
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from typing import Optional

def upload_file_to_s3(file_path: str, bucket: str, key: str, content_type: Optional[str] = None) -> bool:
    """
    指定したファイルをS3にアップロードする
    :param file_path: ローカルファイルパス
    :param bucket: S3バケット名
    :param key: S3オブジェクトキー（パス含む）
    :param content_type: Content-Type（省略可）
    :return: 成功時True, 失敗時False
    """
    session = boto3.session.Session()
    s3 = session.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        aws_session_token=os.getenv('AWS_SESSION_TOKEN'),
        region_name=os.getenv('AWS_REGION')
    )
    extra_args = {'ContentType': content_type} if content_type else {}
    try:
        s3.upload_file(file_path, bucket, key, ExtraArgs=extra_args)
        print(f"✓ S3アップロード成功: s3://{bucket}/{key}")
        return True
    except (BotoCoreError, ClientError) as e:
        print(f"S3アップロード失敗: {e}")
        return False
