# PostgreSQL + pgvector 관리
import json
import os
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pgvector.psycopg import register_vector

from models import VectorSearchResult
from config import SEARCH_SCORE_THRESHOLD, EMBEDDING_DIM


class PostgresVectorManager:
    """PostgreSQL + pgvector 관리 매니저"""

    def __init__(
        self,
        db_url: str,
        embedding_model: Any,
        table_name: str = "investment_knowledge",
    ):
        self.db_url = db_url
        self.table_name = table_name
        self.embedding_model = embedding_model
        self.embedding_dim = EMBEDDING_DIM

        # 연결 풀 생성
        self.pool = ConnectionPool(conninfo=db_url, min_size=1, max_size=10)
        
        # 스키마 초기화
        self._init_db()
        print(f"✅ PostgreSQL(pgvector) 초기화 완료")
        print(f"  📚 테이블: {table_name}")
        print(f"  🧠 임베딩 차원: {self.embedding_dim}")

    def _init_db(self):
        """테이블 및 확장 기능 초기화"""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                # 1. pgvector 확장 기능 활성화
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                
                # 2. 테이블 생성 (UUID, content, metadata, embedding)
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        content TEXT NOT NULL,
                        metadata JSONB,
                        embedding vector({self.embedding_dim}),
                        added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # 3. HNSW 인덱스 생성 (검색 성능 최적화)
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx 
                    ON {self.table_name} USING hnsw (embedding vector_cosine_ops);
                """)
                conn.commit()

    def add_documents(self, documents: List, doc_type: str = "raw") -> int:
        """문서들을 PostgreSQL에 저장"""
        added_count = 0
        
        with self.pool.connection() as conn:
            # pgvector 등록 (각 연결마다 필요)
            register_vector(conn)
            
            with conn.cursor() as cur:
                for doc in documents:
                    if hasattr(doc, "page_content"):
                        content = doc.page_content
                        metadata = dict(doc.metadata) if hasattr(doc, "metadata") else {}
                    elif isinstance(doc, dict):
                        content = doc.get("content", "")
                        metadata = {k: v for k, v in doc.items() if k != "content"}
                    else:
                        continue

                    if not content.strip():
                        continue

                    # 메타데이터 정리
                    metadata["type"] = doc_type
                    
                    # 임베딩 생성 (OpenAI API 호출)
                    embedding = self.embedding_model.encode(content)

                    # 저장
                    cur.execute(
                        f"INSERT INTO {self.table_name} (content, metadata, embedding) VALUES (%s, %s, %s)",
                        (content, json.dumps(metadata), embedding)
                    )
                    added_count += 1
                
                conn.commit()
        
        print(f"✅ {added_count}개 문서 PostgreSQL 저장 완료")
        return added_count

    def search(
        self,
        query: str,
        k: int = 5,
        metadata_filter: Optional[Dict] = None,
        score_threshold: float = SEARCH_SCORE_THRESHOLD,
    ) -> Tuple[List[VectorSearchResult], float]:
        """pgvector 기반 코사인 유사도 검색"""
        try:
            print(f"\n  [Postgres 검색] {query}")
            query_embedding = self.embedding_model.encode(query)
            
            search_results: List[VectorSearchResult] = []
            total_score = 0.0

            with self.pool.connection() as conn:
                register_vector(conn)
                with conn.cursor(row_factory=dict_row) as cur:
                    # 코사인 유사도: 1 - (embedding <=> query_embedding)
                    # <=> : cosine distance
                    sql = f"""
                        SELECT id, content, metadata, 
                               1 - (embedding <=> %s) AS similarity
                        FROM {self.table_name}
                        WHERE 1 - (embedding <=> %s) >= %s
                        ORDER BY similarity DESC
                        LIMIT %s
                    """
                    cur.execute(sql, (query_embedding, query_embedding, score_threshold, k))
                    rows = cur.fetchall()

                    for row in rows:
                        search_results.append(
                            VectorSearchResult(
                                id=str(row["id"]),
                                content=row["content"],
                                similarity_score=float(row["similarity"]),
                                metadata=row["metadata"] or {},
                                type=row["metadata"].get("type", "unknown") if row["metadata"] else "unknown"
                            )
                        )
                        total_score += float(row["similarity"])

            coverage = (total_score / k) if k > 0 else 0.0
            print(f"     결과 {len(search_results)}건 / 커버리지 {coverage:.2%}")
            return search_results, coverage

        except Exception as e:
            print(f"❌ 검색 실패: {e}")
            import traceback
            traceback.print_exc()
            return [], 0.0

    def count_documents(self) -> int:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {self.table_name}")
                result = cur.fetchone()
                return result[0] if result else 0

    def get_stats(self) -> Dict:
        count = self.count_documents()
        return {
            "total_documents": count,
            "engine": "PostgreSQL + pgvector",
            "table_name": self.table_name,
            "embedding_dimension": self.embedding_dim
        }

    def clear(self) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"TRUNCATE TABLE {self.table_name}")
                conn.commit()
        print("✅ DB 테이블 초기화 완료")
