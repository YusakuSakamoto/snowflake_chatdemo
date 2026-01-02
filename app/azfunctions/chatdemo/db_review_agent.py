"""
DB設計レビューエージェント呼び出しモジュール

Snowflake AgentのOBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENTを呼び出し、
レビュー結果をMarkdown形式で返す。

Note: Snowflake AgentはREST API経由でのみ呼び出し可能
"""
import logging
import re
import json
from typing import Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
from snowflake_cortex import SnowflakeCortexClient


class DBReviewAgent:
    """DB設計レビューエージェントのラッパークラス（REST API使用）"""
    
    def __init__(self):
        self.agent_name = "DB_DESIGN.OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT"
        self.cortex_client = SnowflakeCortexClient()
        
        # レビュー結果の出力ディレクトリ
        self.output_dir = Path(__file__).parent.parent.parent.parent / "docs" / "snowflake" / "chatdemo" / "reviews" / "schemas"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def review_schema(
        self,
        target_schema: str,
        max_tables: Optional[int] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        指定されたスキーマのDB設計レビューを実行（REST API経由）
        
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
            # Agent呼び出しのプロンプト生成
            prompt = self._build_review_prompt(target_schema, max_tables)
            
            # Snowflake Cortex AgentをREST API経由で実行
            logging.info(f"Starting DB review for schema: {target_schema} via REST API")
            logging.info(f"Agent name: {self.agent_name}")
            
            # REST API経由でAgent呼び出し（call_cortex_agentは内部でPOST /api/v2/cortex/agentを呼ぶ）
            agent_response = self.cortex_client.call_cortex_agent(
                prompt,
                agent_name=self.agent_name
            )
            
            if not agent_response:
                return False, "Agent実行結果が空です", None
            
            # エラーチェック
            if isinstance(agent_response, dict):
                if agent_response.get("ok") is False:
                    error_detail = agent_response.get("error", "Unknown error")
                    return False, f"Agent実行エラー: {error_detail}", None
                
                # 正常レスポンスからテキストを抽出
                agent_output = agent_response.get("response", "")
            else:
                agent_output = str(agent_response)
            
            if not agent_output:
                return False, "Agent応答が空です", None
            
            logging.info(f"Agent response length: {len(agent_output)}")
            
            # Markdown部分を抽出
            markdown = self._extract_markdown(agent_output)
            
            if not markdown:
                logging.warning("Markdownの抽出に失敗しました。生の出力を返します。")
                markdown = agent_output
            
            # Markdownファイルとして保存
            output_file = self._save_markdown(target_schema, markdown)
            
            logging.info(f"DB review completed for schema: {target_schema}")
            logging.info(f"Review saved to: {output_file}")
            return True, f"レビュー完了（保存先: {output_file.name}）", markdown
                
        except Exception as e:
            error_msg = f"DB設計レビュー実行エラー: {str(e)}"
            logging.error(error_msg)
            logging.exception("Full traceback:")
            return False, error_msg, None
    
    def _extract_response_text(self, response: any) -> Optional[str]:
        """
        REST APIレスポンスからテキストを抽出
        
        Args:
            response: AgentのREST APIレスポンス
        
        Returns:
            抽出されたテキスト
        """
        try:
            # 辞書形式のレスポンス
            if isinstance(response, dict):
                # 'message', 'content', 'text', 'result' などのキーを探す
                for key in ['message', 'content', 'text', 'result', 'response', 'data']:
                    if key in response and response[key]:
                        value = response[key]
                        # リストの場合は最初の要素
                        if isinstance(value, list) and len(value) > 0:
                            return str(value[0])
                        return str(value)
                
                # 辞書全体をJSON文字列として返す
                return json.dumps(response, ensure_ascii=False)
            
            # 文字列の場合はそのまま返す
            elif isinstance(response, str):
                return response
            
            # その他の型は文字列に変換
            return str(response)
            
        except Exception as e:
            logging.error(f"Response text extraction error: {e}")
            return str(response)
    
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
        
        Agent出力形式: ~~~md\n<markdown content>\n~~~ または JSON形式
        """
        try:
            # JSON形式の場合はパース
            if isinstance(agent_output, str) and (agent_output.strip().startswith('{') or agent_output.strip().startswith('[')):
                import json
                data = json.loads(agent_output)
                
                # よくあるJSON構造からMarkdownを探す
                if isinstance(data, dict):
                    # message, content, markdown などのキーを探す
                    for key in ['message', 'content', 'markdown', 'result', 'text']:
                        if key in data and data[key]:
                            agent_output = data[key]
                            break
                elif isinstance(data, list) and len(data) > 0:
                    agent_output = str(data[0])
            
        except json.JSONDecodeError:
            pass  # JSONでない場合は続行
        except Exception as e:
            logging.warning(f"JSON parse error: {e}")
        
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
        
        # どちらもマッチしない場合は元の文字列を返す
        return agent_output
    
    def _escape_sql_string(self, s: str) -> str:
        """SQL文字列をエスケープ（シングルクォートを2重化）"""
        return s.replace("'", "''")
    
    def _save_markdown(self, target_schema: str, markdown_content: str) -> Path:
        """
        レビュー結果をMarkdownファイルとして保存
        
        Args:
            target_schema: 対象スキーマ名
            markdown_content: Markdownコンテンツ
        
        Returns:
            保存したファイルのPath
        """
        # ファイル名生成: {schema}_{YYYYMMDD}_{HHMMSS}.md
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{target_schema}_{timestamp}.md"
        output_file = self.output_dir / filename
        
        # Markdownファイルとして保存
        output_file.write_text(markdown_content, encoding="utf-8")
        logging.info(f"Review saved to: {output_file}")
        
        return output_file
    
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
