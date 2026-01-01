# Git運用規則

## 概要
本ドキュメントは、snowflake_chatdemoプロジェクトにおけるGit運用規則を定義します。

---

## ブランチ戦略

### メインブランチ
- `main` - 本番環境と同期するブランチ
  - すべてのコミットは安定した状態を保つ
  - 直接pushは可能だが、レビューを推奨

### 作業ブランチ（必要に応じて）
- `feature/*` - 新機能開発用
- `fix/*` - バグ修正用
- `docs/*` - ドキュメント更新用

---

## コミットメッセージ規則

### 基本原則
**すべてのコミットメッセージは日本語で記載する**

### プレフィックスの使用
コミットの種類を明確にするため、以下のプレフィックスを使用します：

| プレフィックス | 用途 | 例 |
|---|---|---|
| `feat:` | 新機能追加 | `feat: V_CUSTOMER_MASTERビューの設計ドキュメント追加` |
| `fix:` | バグ修正 | `fix: カラム名参照のバッククォートをObsidianリンクに修正` |
| `docs:` | ドキュメント更新 | `docs: メンテナンスガイドとスクリプトREADMEを追加・更新` |
| `refactor:` | リファクタリング | `refactor: 命名規則に従ってDOCS_OBSIDIAN_VをV_DOCS_OBSIDIANにリネーム` |
| `style:` | フォーマット修正 | `style: Markdownファイルのインデント統一` |
| `test:` | テスト追加・修正 | `test: Snowflake接続テストスクリプト追加` |
| `chore:` | ビルド・環境設定 | `chore: Python依存関係を更新` |

### 良いコミットメッセージの例
```bash
git commit -m "feat: プロファイル結果のエクスポート機能追加"
git commit -m "fix: 平文のオブジェクト名もmasterリンクに修正"
git commit -m "docs: 命名規則ドキュメント作成とObsidianリンク追加"
git commit -m "refactor: バッククォートの包括的クリーンアップ"
git commit -m "fix: 実体参照時はmasterファイルへのリンクに修正"
```

### 悪いコミットメッセージの例
```bash
# 英語（禁止）
git commit -m "Update files"
git commit -m "Fix bug"
git commit -m "Add new view"

# 曖昧すぎる
git commit -m "修正"
git commit -m "更新"
git commit -m "変更"

# プレフィックスなし（推奨されない）
git commit -m "カラム名を修正"
```

### コミットメッセージの構成
```
<プレフィックス>: <簡潔な説明>

[オプション: 詳細な説明]
[オプション: 関連Issue番号]
```

#### 例：詳細説明付き
```bash
git commit -m "feat: PROFILE_ALL_TABLESプロシージャ追加

スキーマ全体のテーブルをループしてプロファイル実行する
オーケストレーション用プロシージャを実装。

- サンプリング率の指定が可能
- 実行履歴をPROFILE_RUNSに記録
- エラー時も処理を継続"
```

---

## コミット前チェックリスト

### 必須チェック項目
- [ ] **Windows Vaultに同期済み**
  ```bash
  rsync -av --delete docs/snowflake/chatdemo/ /mnt/c/Users/Owner/Documents/snowflake-db/
  ```
- [ ] **コミットメッセージが日本語**
- [ ] **適切なプレフィックスを使用**

### 推奨チェック項目
- [ ] 変更内容をgit diffで確認済み
- [ ] 不要なファイルが含まれていない
- [ ] 命名規則に準拠している
- [ ] バッククォートが残っていない
- [ ] リンクが正しく設定されている

---

## コミット手順

### 標準的なワークフロー
```bash
# 1. 変更内容の確認
git status
git diff

# 2. ファイルをステージング
git add docs/snowflake/chatdemo/design/DB_DESIGN/design.OBJECT.md

# または全ファイルを追加
git add -A

# 3. コミット（日本語メッセージ）
git commit -m "feat: 新しいビューの設計ドキュメント追加"

# 4. プッシュ
git push
```

### Windows Vault同期を含むワークフロー
```bash
# 1. Windows Vaultに同期
rsync -av --delete docs/snowflake/chatdemo/ /mnt/c/Users/Owner/Documents/snowflake-db/

# 2. 変更を確認
git status

# 3. コミット・プッシュ
git add -A
git commit -m "docs: ドキュメント更新とWindows Vault同期"
git push
```

---

## 特殊な操作

### コミットメッセージの修正

#### 直前のコミットメッセージを修正
```bash
git commit --amend -m "fix: 修正後の日本語メッセージ"
git push --force-with-lease
```

#### 過去のコミットメッセージを一括修正
```bash
# filter-branchを使用（例：最近7件を修正）
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --msg-filter '
  case "$(cat)" in
    "Old English message") echo "新しい日本語メッセージ" ;;
    *) cat ;;
  esac
' HEAD~7..HEAD

# force push
git push --force-with-lease
```

**注意：** force pushは履歴を書き換えるため、他の開発者と共有しているブランチでは慎重に使用してください。

### コミットの取り消し

#### 直前のコミットを取り消し（変更は保持）
```bash
git reset --soft HEAD~1
```

#### 直前のコミットを完全に取り消し
```bash
git reset --hard HEAD~1
```

### ファイルの履歴確認
```bash
# ファイルの変更履歴を表示
git log --oneline -- docs/snowflake/chatdemo/design/DB_DESIGN/design.OBJECT.md

# 特定のコミットでの変更内容を表示
git show <commit-hash>
```

---

## .gitignoreルール

### 無視するファイル
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
ENV/

# IDEs
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.bak
*~

# Logs
*.log

# Obsidian
.obsidian/workspace
.obsidian/workspace.json
.obsidian/plugins/remotely-save/data.json
```

### バージョン管理するObsidianファイル
- `.obsidian/app.json` - アプリ設定
- `.obsidian/appearance.json` - 外観設定
- `.obsidian/community-plugins.json` - プラグインリスト
- `.obsidian/plugins/*/manifest.json` - プラグイン設定
- テンプレート、スニペット、テーマファイル

---

## トラブルシューティング

### コンフリクトの解決
```bash
# 1. コンフリクト発生時
git pull
# CONFLICT (content): Merge conflict in <file>

# 2. ファイルを手動で編集してコンフリクトマーカーを削除
# <<<<<<< HEAD
# =======
# >>>>>>> branch-name

# 3. 解決後にコミット
git add <resolved-file>
git commit -m "fix: コンフリクト解決"
git push
```

### 誤ってコミットしたファイルの削除
```bash
# ファイルをGit管理から削除（ファイル自体は残す）
git rm --cached <file>
git commit -m "chore: 不要なファイルをGit管理から削除"
git push
```

### リモートの変更を強制的に上書き
```bash
# ローカルの変更を破棄してリモートと同期
git fetch origin
git reset --hard origin/main
```

---

## CI/CD（将来の拡張）

### GitHub Actions（検討中）
- コミットメッセージのバリデーション（日本語チェック）
- markdownlintによるドキュメント品質チェック
- リンク切れチェック
- バッククォート残存チェック
- 命名規則違反チェック

---

## 参考資料

- [MAINTENANCE_GUIDE.md](../../snowflake/chatdemo/MAINTENANCE_GUIDE.md) - メンテナンスガイド
- [naming_conventions.md](../../snowflake/chatdemo/naming_conventions.md) - 命名規則
- [Conventional Commits](https://www.conventionalcommits.org/) - コミットメッセージ規約の参考

---

## 変更履歴

| 日付 | 変更内容 |
|------|---------|
| 2026-01-02 | 初版作成：Git運用規則を定義 |
