#!/bin/bash

# Snowflake接続確認スクリプト

echo "=========================================="
echo "Snowflake接続テスト"
echo "=========================================="
echo ""

# 現在のIPアドレスを表示
echo "📍 現在のIPアドレス:"
CURRENT_IP=$(curl -s https://api.ipify.org)
echo "   外部IP: $CURRENT_IP"
echo ""

# SnowSQLの接続情報を表示
echo "🔐 SnowSQL接続設定:"
echo "   Account: pgpalab-iy16795"
echo "   User: YUSAKURO"
echo "   Private Key: /home/yolo/.ssh/snowflake/rsa_key.p8"
echo ""

# SnowSQLで接続テスト
echo "🔄 接続テスト中..."
echo ""

snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -q "SELECT CURRENT_VERSION(), CURRENT_USER(), CURRENT_ACCOUNT(), CURRENT_REGION();"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 接続成功！"
    echo ""
    
    # 追加情報を取得
    echo "📊 データベース情報:"
    snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -q "SHOW DATABASES;" -o output_format=table
    
    echo ""
    echo "🏢 ウェアハウス情報:"
    snowsql -c myconn --private-key-path /home/yolo/.ssh/snowflake/rsa_key.p8 -q "SHOW WAREHOUSES;" -o output_format=table
    
else
    echo ""
    echo "❌ 接続失敗"
    echo ""
    echo "💡 トラブルシューティング:"
    echo "   1. ネットワークポリシーでIPアドレス $CURRENT_IP が許可されているか確認"
    echo "   2. 秘密鍵のパスが正しいか確認: /home/yolo/.ssh/snowflake/rsa_key.p8"
    echo "   3. ユーザーに秘密鍵が登録されているか確認"
    echo ""
fi
