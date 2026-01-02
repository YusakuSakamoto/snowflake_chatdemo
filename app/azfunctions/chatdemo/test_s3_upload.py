"""
S3アップロード関数の動作テスト
"""
from s3_upload import upload_file_to_s3
import os

def main():
    # テスト用ファイルを作成
    test_file = "test_upload.txt"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("S3 upload test: これはテストファイルです\n")

    # S3バケット・キー（適宜書き換え）
    bucket = os.getenv("TEST_S3_BUCKET") or "135365622922-snowflake-chatdemo-logs-prod"
    key = "test/test_upload.txt"

    # アップロード実行
    result = upload_file_to_s3(test_file, bucket, key, content_type="text/plain")
    print("アップロード結果:", result)

    # 後始末
    os.remove(test_file)

if __name__ == "__main__":
    main()
