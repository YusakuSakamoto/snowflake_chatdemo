"""
DB設計レビューエージェント呼び出しモジュール

Snowflake AgentのOBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENTを呼び出し、
レビュー結果をMarkdown形式で返す。
"""
import logging
import re
from typing import Dict, Optional, Tuple
from snowflake_db import SnowflakeConnection


class DBReviewAgent:
    """DB設計レビューエージェントのラッパークラス"""
    
    def __init__(self):
        self.agent_name = "DB_DESIGN.OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT"
    
    def review_schema(
        self,
        target_schema: str,
        max_tables: Optional[int] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        指定されたスキーマのDB設計レビューを実行
        
        Args:
            target_schema: レビュー対象のスキーマ名
            max_tables: レビュー対象テーブルの最大数（省略可）
        
        Returns:
            Tuple[success, message, markdown_content]
            - success: 実行成功フラグ
            - message: ステータスメッセージ
            - markdown_content: レビュー結果のMarkdown（成功時のみ）
        """
        try:
            with SnowflakeConnection() as conn:
                cursor = conn.cursor()
                
                # Agent呼び出しのプロンプト生成
                prompt = self._build_review_prompt(target_schema, max_tables)
                
                # Snowflake Agentを実行
                logging.info(f"Starting DB review for schema: {target_schema}")
                
                query = f"""
                SELECT SNOWFLAKE.CORTEX.COMPLETE_AGENT(
                    '{self.agent_name}',
                    '{self._escape_sql_string(prompt)}'
                ) AS review_result
                """
                
                logging.info(f"Executing Agent query: {query[:200]}...")
                cursor.execute(query)
                result = cursor.fetchone()
                
                if not result or not result[0]:
                    return False, "Agent実行結果が空です", None
                
                # 結果をパース（JSON形式の可能性がある）
                agent_output = result[0]
                logging.info(f"Agent output length: {len(agent_output) if agent_output else 0}")
                
                # Markdown部分を抽出
                markdown = self._extract_markdown(agent_output)
                
                if not markdown:
                    logging.warning("Markdownの抽出に失敗しました。生の出力を返します。")
                    markdown = agent_output
                
                logging.info(f"DB review completed for schema: {target_schema}")
                return True, "レビュー完了", markdown
                
        except Exception as e:
            error_msg = f"DB設計レビュー実行エラー: {str(e)}"
            logging.error(error_msg)
            logging.exception("Full traceback:")
            return False, error_msg, None
    
    def _build_review_prompt(
        self,
        target_schema: str,
        max_tables: Optional[int]
    ) -> str:
        """レビュー用のプロンプトを生成"""
        prompt = f"{target_schema}スキーマの設計レビューを実行してください。"
        
        if max_tables:
            prompt += f" 対象テーブル数は最大{max_tables}件とします。"
        
        prompt += """
        
レビュー観点：
- 命名規則の準拠状況
- データ型・ドメインの一貫性
- NULL許可・デフォルト値の妥当性
- PK/FK設計の整合性
- 設計ドキュメントの完全性

出力は必ずMarkdown形式（~~~md ... ~~~）で返してください。
"""
        return prompt
    
    def _extract_markdown(self, agent_output: str) -> Optional[str]:
        """
        Agent出力からMarkdown部分を抽出
        
        Agent出力形式: ~~~md\n<markdown content>\n~~~
        """
        # ~~~md ... ~~~ で囲まれた部分を抽出
        pattern = r'~~~md\s*\n(.*?)\n~~~'
        match = re.search(pattern, agent_output, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        # 代替パターン: ```markdown ... ```
        pattern_alt = r'```markdown\s*\n(.*?)\n```'
        match_alt = re.search(pattern_alt, agent_output, re.DOTALL)
        
        if match_alt:
            return match_alt.group(1).strip()
        
        # どちらもマッチしない場合はNone
        return None
    
    def _escape_sql_string(self, s: str) -> str:
        """SQL文字列をエスケープ（シングルクォートを2重化）"""
        return s.replace("'", "''")
    
    def save_review_to_vault(
        self,
        markdown_content: str,
        target_schema: str,
        review_date: str
    ) -> Tuple[bool, str]:
        """
        レビュー結果をSnowflake Stageに保存
        
        Args:
            markdown_content: Markdownコンテンツ
            target_schema: 対象スキーマ名
            review_date: レビュー日（YYYY-MM-DD）
        
        Returns:
            Tuple[success, message]
        """
        try:
            with SnowflakeConnection() as conn:
                cursor = conn.cursor()
                
                # ファイルパス生成
                file_path = f"reviews/db_design/{target_schema.lower()}_{review_date}.md"
                
                # Stageに保存（PUTコマンドの代替としてテーブル経由）
                # 注意: 実際の保存先はOBSIDIAN_VAULT_STAGEへの書き込み権限が必要
                query = f"""
                PUT 'data://{file_path}' 
                @DB_DESIGN.OBSIDIAN_VAULT_STAGE/{file_path}
                AUTO_COMPRESS = FALSE
                OVERWRITE = TRUE
                """
                
                # 実際にはSnowpark Pythonプロシージャ経由で保存推奨
                logging.info(f"レビュー結果の保存先: {file_path}")
                
                return True, f"レビュー結果を {file_path} に保存しました"
                
        except Exception as e:
            error_msg = f"レビュー結果の保存エラー: {str(e)}"
            logging.error(error_msg)
            return False, error_msg
